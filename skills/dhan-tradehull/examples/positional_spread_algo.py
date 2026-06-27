from Dhan_Tradehull import Tradehull
from rich import print
import talib
import pandas as pd
import datetime
import xlwings as xw
import pretty_errors
import tradehull_backtesting as tb
import os
import pdb
import time
import json




client_code           = "YOUR_CLIENT_CODE"
access_token          = "YOUR_ACCESS_TOKEN"
tsl                   = Tradehull(client_code, access_token)
watchlist             = ['NIFTY','TCS', 'WIPRO']
status                = {'traded':None, 'options_name':None}
re_entry              = False
EXIT_TIME             = datetime.time(23, 35, 59)
ENTRY_TIME            = datetime.time(9, 35, 40)

with open("positional_orderbook.json", "r") as f:
	loaded_data = json.load(f)
	orderbook             = loaded_data['orderbook']
	complted_orderbook    = loaded_data['complted_orderbook']





while True:

	current_dt     = datetime.datetime.now()
	current_time   = current_dt.time()

	if current_time < ENTRY_TIME:
		print(f"{current_time}Waiting for the market to open")
		continue

	current_pnl  = tsl.get_live_pnl()
	market_over  = current_time > EXIT_TIME


	
	if market_over:
		print(f"{current_time} Exiting the Algo")


		with open("positional_orderbook.json", "w") as f:
			send_data = {'orderbook':orderbook, 'complted_orderbook':complted_orderbook}
			json.dump(send_data, f, indent=4)




		dhan_orderbook = tsl.get_orderbook()
		logs           = pd.DataFrame(orderbook).T
		positionbook   = tsl.get_positions()

		path = f"Logs/{str(datetime.datetime.now().date())}"
		os.makedirs(f"{path}", exist_ok=True)

		dhan_orderbook.to_csv(f"{path}/dhan_orderbook.csv")
		logs.to_csv(f"{path}/logs.csv")
		positionbook.to_csv(f"{path}/positionbook.csv")

		break






	for name in watchlist:        


		chart        = tsl.get_historical_data(tradingsymbol='NIFTY', exchange='INDEX', timeframe="60")
		chart        = chart.set_index('timestamp')
		chart        = tb.supertrend(df=chart, atr_period=10, atr_multiplier=3)
		comp_candle  = chart.iloc[-1]


		
		bc1 = comp_candle['STX_10_3'] == 'up'
		bc2 = orderbook[name]['traded'] is None

		sc1 = comp_candle['STX_10_3'] == 'down'
		sc2 = orderbook[name]['traded'] is None


		# -------------------------------------------- Bullish Block Sell Puts  --------------------------------------------

		if bc1 and bc2:
			print(f"{name}  Uptrend")

			expiry_no    = tsl.get_expiry_list('NIFTY', 'INDEX').index(tsl.get_expiry_list('NIFTY', 'NFO')[1])
			atm, oc      = tsl.get_option_chain(Underlying="NIFTY", exchange="INDEX", expiry=expiry_no, num_strikes=50)


			oc['PE Delta']           = abs(oc['PE Delta'])
			selling_strike           = str(int(oc[oc['PE Delta'].between(0.10, 0.16)].sort_values('PE OI').iloc[-1]['Strike Price']))
			hedging_strike           = str(int(oc[oc['PE Delta'].between(0.07, 0.09)].sort_values('PE OI').iloc[-1]['Strike Price']))

			ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=expiry_no)
			nap                      = ce_name.split(" ")  # name parts
			selling_name             = f"{name} {nap[1]} {nap[2]} {selling_strike} PUT"
			hedging_name             = f"{name} {nap[1]} {nap[2]} {hedging_strike} PUT"

			lot_size                 = tsl.get_lot_size(selling_name)


			options_ltp            = tsl.get_ltp_data(names=[selling_name, hedging_name])
			selling_ltp            = options_ltp[selling_name]
			hedging_ltp            = options_ltp[hedging_name]

			hedging_entry_price   = round(hedging_ltp * 1.03, 1)
			selling_entry_price   = round(selling_ltp * 0.97, 1)
			selling_exit_price    = round(selling_ltp * 1.03, 1)

			try:
				hedging_orderid  = tsl.order_placement(tradingsymbol=hedging_name, exchange='NFO', quantity=lot_size, price=hedging_entry_price, trigger_price=0,order_type='LIMIT', transaction_type='BUY', trade_type='MARGIN', amo_time='OPEN', after_market_order=True )
				time.sleep(1)
				hedging_status = tsl.get_order_status(orderid=hedging_orderid)

				if hedging_status == 'suscessfull':
					selling_orderid  = tsl.order_placement(tradingsymbol=selling_name, exchange='NFO', quantity=lot_size, price=selling_entry_price, trigger_price=0,order_type='LIMIT', transaction_type='SELL', trade_type='MARGIN', amo_time='OPEN', after_market_order=True)
					time.sleep(1)
					selling_status = tsl.get_order_status(orderid=selling_orderid)
					if selling_status == 'un-suscessfull':
						exit_hedging   = tsl.order_placement(tradingsymbol=hedging_name, exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='LIMIT', transaction_type='SELL', trade_type='MARGIN', amo_time='OPEN', after_market_order=True)
				else:
					continue

			except Exception as e:
				print(e)
				continue









			orderbook[name]['selling_name']      = selling_name
			orderbook[name]['hedging_name']      = hedging_name

			orderbook[name]['selling_orderid']    = selling_orderid
			orderbook[name]['hedging_orderid']    = hedging_orderid
			orderbook[name]['qty']                = lot_size

			orderbook[name]['selling_price']      = tsl.get_executed_price(orderid=orderbook[name]['selling_orderid'])
			orderbook[name]['hedging_price']      = tsl.get_executed_price(orderid=orderbook[name]['hedging_orderid'])
			orderbook[name]['max_profit']         = (orderbook[name]['selling_price'] - orderbook[name]['hedging_price'])*orderbook[name]['qty']

			orderbook[name]['sl_pnl']            = round(orderbook[name]['max_profit']*0.7*-1, 2)
			orderbook[name]['tg_pnl']            = round(orderbook[name]['max_profit']*0.7*1,  2)

			orderbook[name]['date']              = str(datetime.datetime.now())
			orderbook[name]['view']              = 'Bullish'
			orderbook[name]['traded']            = True
			orderbook[name]['expiry']            = tsl.get_expiry_list('NIFTY', 'NFO')[1]


		# -------------------------------------------- Bearish Block Sell Calls  --------------------------------------------

		if sc1 and sc2:
			print(f"{name}  Downtrend")

			expiry_no    = tsl.get_expiry_list('NIFTY', 'INDEX').index(tsl.get_expiry_list('NIFTY', 'NFO')[1])
			atm, oc      = tsl.get_option_chain(Underlying="NIFTY", exchange="INDEX", expiry=expiry_no, num_strikes=50)

			selling_strike           = str(int(oc[oc['CE Delta'].between(0.10, 0.16)].sort_values('CE OI').iloc[-1]['Strike Price']))
			hedging_strike           = str(int(oc[oc['CE Delta'].between(0.07, 0.09)].sort_values('CE OI').iloc[-1]['Strike Price']))

			ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=expiry_no)
			nap                      = ce_name.split(" ")  # name parts
			selling_name             = f"{name} {nap[1]} {nap[2]} {selling_strike} CALL"
			hedging_name             = f"{name} {nap[1]} {nap[2]} {hedging_strike} CALL"

			lot_size                 = tsl.get_lot_size(selling_name)


			options_ltp            = tsl.get_ltp_data(names=[selling_name, hedging_name])
			selling_ltp            = options_ltp[selling_name]
			hedging_ltp            = options_ltp[hedging_name]
			
			selling_entry_price    = selling_ltp * 0.995
			hedging_entry_price    = hedging_ltp * 1.005
			selling_exit_price     = selling_ltp * 1.005


			try:
				hedging_orderid  = tsl.order_placement(tradingsymbol=hedging_name, exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='LIMIT', transaction_type='BUY', trade_type='MARGIN')
				time.sleep(1)
				hedging_status = tsl.get_order_status(orderid=hedging_orderid)

				if hedging_status == 'TRADED':

					selling_orderid  = tsl.order_placement(tradingsymbol=selling_name, exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='LIMIT', transaction_type='SELL', trade_type='MARGIN')
					time.sleep(1)
					selling_status = tsl.get_order_status(orderid=selling_orderid)

					if selling_status != 'TRADED':
						exit_selling   = tsl.order_placement(tradingsymbol=selling_name, exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='LIMIT', transaction_type='BUY', trade_type='MARGIN')

			except Exception as e:
				print(e)
				continue




			orderbook[name]['selling_name']      = selling_name
			orderbook[name]['hedging_name']      = hedging_name

			orderbook[name]['selling_orderid']    = selling_orderid
			orderbook[name]['hedging_orderid']    = hedging_orderid
			orderbook[name]['qty']                = lot_size

			orderbook[name]['selling_price']      = tsl.get_executed_price(orderid=orderbook[name]['selling_orderid'])
			orderbook[name]['hedging_price']      = tsl.get_executed_price(orderid=orderbook[name]['hedging_orderid'])
			orderbook[name]['max_profit']         = (orderbook[name]['selling_price'] - orderbook[name]['hedging_price'])*orderbook[name]['qty']

			orderbook[name]['sl_pnl']            = round(orderbook[name]['max_profit']*0.7*-1, 2)
			orderbook[name]['tg_pnl']            = round(orderbook[name]['max_profit']*0.7*1,  2)

			orderbook[name]['date']              = str(datetime.datetime.now())
			orderbook[name]['view']              = 'Bearish'
			orderbook[name]['traded']            = True
			orderbook[name]['expiry']            = tsl.get_expiry_list('NIFTY', 'NFO')[1]


		# -------------------------------------------- Trailing Stop Loss and Take Profit  --------------------------------------------


		if orderbook[name]['traded']:

			bullish = orderbook[name]['view'] == 'Bullish'
			bearish = orderbook[name]['view'] == 'Bearish'

			if bullish or bearish:

				ltps                    = tsl.get_ltp_data(names=[orderbook[name]['selling_name'], orderbook[name]['hedging_name']])
				sold_ltp                = ltps[orderbook[name]['selling_name']]
				hedged_ltp              = ltps[orderbook[name]['hedging_name']]

				selling_pnl             = (orderbook[name]['selling_price'] - sold_ltp)*orderbook[name]['qty']
				hedging_pnl             = (hedged_ltp - orderbook[name]['hedging_price'])*orderbook[name]['qty']

				orderbook[name]['pnl']  = selling_pnl + hedging_pnl

				sl_hit                  = orderbook[name]['pnl'] <  orderbook[name]['sl_pnl']
				tg_hit                  = orderbook[name]['pnl'] >  orderbook[name]['tg_pnl']
				only_few_days_left      = ((pd.to_datetime(orderbook[name]['expiry']) - datetime.datetime.now()).days < 30) and  (datetime.datetime.now().time() > datetime.time(14, 30))



				if bullish:
					trailing_exit   = comp_candle['STX_10_3'] == 'down'
				if bearish:
					trailing_exit   = comp_candle['STX_10_3'] == 'up'


				if trailing_exit or sl_hit or tg_hit or only_few_days_left:


					selling_exit_orderid  = tsl.order_placement(tradingsymbol=orderbook[name]['selling_name'], exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='LIMIT', transaction_type='BUY', trade_type='MARGIN')
					time.sleep(2)
					hedging_exit_orderid  = tsl.order_placement(tradingsymbol=orderbook[name]['hedging_price'], exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='LIMIT', transaction_type='SELL', trade_type='MARGIN')


					orderbook[name]['selling_exit_orderid'] = selling_exit_orderid
					orderbook[name]['hedging_exit_orderid'] = hedging_exit_orderid

					remark                                 = "trailing_exit" if trailing_exit else "sl_hit" if sl_hit else "tg_hit" if tg_hit else "only_few_days_left" if only_few_days_left else None
					orderbook[name]['selling_exit_price']  = tsl.get_executed_price(orderid=orderbook[name]['selling_exit_orderid'])
					orderbook[name]['hedging_exit_price']  = tsl.get_executed_price(orderid=orderbook[name]['hedging_exit_orderid'])
					orderbook[name]['exit_time']           = str(datetime.datetime.now())
					orderbook[name]['remark']              = remark

					complted_orderbook.append(orderbook[name])						
					orderbook[name] = status.copy()



