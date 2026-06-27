# NOTE: This algo was written before the SEBI MARKET order ban (Apr 1 2026).
# order_type='MARKET' for NFO is now BANNED — must be replaced with LIMIT.
# Pattern: ltp = tsl.get_ltp_data([name])[name]; price = round(ltp * 1.02, 1)
# All logic, structure, and patterns remain valid — only order_type needs updating.
# See references/orders.md for the current LIMIT order pattern.

from Dhan_Tradehull import Tradehull
from rich import print
import talib
import pandas as pd
import datetime
import time
import xlwings as xw
import pretty_errors
import tradehull_backtesting as tb
import os
print()

book                  = xw.Book('Algo1.xlsx')
orderbook_sheet       = book.sheets['Live Orderbook']
completed_sheet       = book.sheets['Completed_Orderbook']
config_sheet          = book.sheets['Strategy Config']
client_code           = str(int(config_sheet.range('B1').value))
access_token          = config_sheet.range('B2').value.replace(" ", "")
tsl                   = Tradehull(client_code, access_token)
watchlist             = [name for name in config_sheet.range('D2:D1000').value if name is not None]
status                = {'traded':None, 'options_name':None}
re_entry              = True
max_orders            = int(config_sheet.range('B10').value)
orderbook             = {name:status.copy() for name in watchlist}
complted_orderbook    = []
EXIT_TIME             = datetime.time(15, 35, 59)
ENTRY_TIME            = datetime.time(9, 35, 40)
opening_balance       = 100000#tsl.get_balance()
max_loss_pct          = config_sheet.range('B9').value
max_loss              = opening_balance * max_loss_pct * -1


orderbook_sheet.range('A1:Z100').value = None
completed_sheet.range('A1:Z100').value = None


# Pre calculate data
sr_data = {}
for name in watchlist:
	print(f"Calculating data for support and resistance for {name}")
	daily         = tsl.get_historical_data(tradingsymbol=name, exchange='NSE', timeframe="DAY")
	sr            = tb.get_support_and_resistance(daily.iloc[-2])
	sr_data[name] = sr
	time.sleep(0.35)



while True:


	current_time = datetime.datetime.now().time()

	if current_time < ENTRY_TIME:
		print(f"{current_time}Waiting for the market to open")
		continue

	current_pnl  = tsl.get_live_pnl()
	market_over  = current_time > EXIT_TIME
	panic_exit   = config_sheet.range('B8').value is not None
	max_loss_hit = current_pnl < max_loss


	# Todo : Testing Pedning
	if market_over or panic_exit or max_loss_hit:
		print(f"{current_time} Exiting the Algo")


		order_details = tsl.cancel_all_orders()
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

		print(f"Scanning {name}")
		odf                               = pd.DataFrame(orderbook).T
		orderbook_sheet.range('A1').value = odf
		completed_sheet.range('A1').value = pd.DataFrame(complted_orderbook)
		current_dt                        = datetime.datetime.now()

		chart        = tsl.get_historical_data(tradingsymbol=name, exchange='NSE', timeframe="5") # in get_start_date.. use timedelta for 15 days only
		chart        = chart.set_index('timestamp')
		chart['rsi'] = talib.RSI(chart['close'], timeperiod=14)
		chart        = tb.supertrend(df=chart, atr_period=15, atr_multiplier=3)

		comp_candle  = pd.Series(datetime.datetime.now()).dt.floor('5min')[0] - datetime.timedelta(minutes=5)
		comp_candle  = comp_candle.strftime("%Y-%m-%d %H:%M:%S+05:30")
		comp_candle  = chart.loc[comp_candle]

		# comp_candle  = chart.iloc[-1]
		sr           = sr_data[name]


		
		bc1 = True#comp_candle['rsi'] > 60
		bc2 = comp_candle['STX_15_3'] == 'up'
		bc3 = orderbook[name]['traded'] is None
		bc4 = comp_candle['close'] > sr['r1']
		bc5 = (len(complted_orderbook) +  odf[odf["traded"].notna()].shape[0]) < max_orders

		sc1 = True#comp_candle['rsi'] < 40
		sc2 = comp_candle['STX_15_3'] == 'down'
		sc3 = orderbook[name]['traded'] is None
		sc4 = comp_candle['close'] < sr['s1']
		sc5 = (len(complted_orderbook) +  odf[odf["traded"].notna()].shape[0]) < max_orders




		# logger.info(f"{name} {bc1} {bc2} {bc3} {bc4} {bc5} {sc1} {sc2} {sc3} {sc4} {sc5}")
		# logger.info(f"{comp_candle}")


		if bc1 and bc2 and bc3 and bc4 and bc5:

			print(f"{name}  Uptrend")
			ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=0)
			lot_size                 = tsl.get_lot_size(ce_name)


			try:
				orderbook[name]['qty']               = lot_size*6
				entry_orderid                        = tsl.order_placement(tradingsymbol=ce_name, exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='MARKET', transaction_type='BUY', trade_type='MIS')
				orderbook[name]['entry_price']       = tsl.get_ltp_data(names=[ce_name])[ce_name] # tsl.get_executed_price(orderid=orderid)
			except Exception as e:
				print(f"Error placing entry order: {e}")
				continue
			
			
			try:
				trigger_price                  = round(orderbook[name]['entry_price']*0.7, 1)
				price                          = max(trigger_price - 0.5, 0.1)
				sl_orderid                     = tsl.order_placement(tradingsymbol=ce_name, exchange='NFO', quantity=lot_size, price=price, trigger_price=trigger_price,order_type='STOPLIMIT', transaction_type='SELL', trade_type='MIS')
			except Exception as e:
				print(f"Error placing SL order: {e}")
				cancel_entry_order             = tsl.cancel_order(OrderID=entry_orderid)
				orderbook[name]                = {'traded':"TRADE_NOT_POSSIBLE", 'options_name':None}
				continue





			orderbook[name]['options_name']      = ce_name
			orderbook[name]['date']              = str(current_dt.date())
			orderbook[name]['entry_time']        = str(current_dt.time())
			orderbook[name]['sl_price']          = trigger_price
			orderbook[name]['tg_price']          = round(orderbook[name]['entry_price']*1.3, 1)
			orderbook[name]['buy_sell']          = 'BUY_CE'
			orderbook[name]['traded']            = True
			orderbook[name]['entry_orderid']     = entry_orderid
			orderbook[name]['sl_orderid']         = sl_orderid
			orderbook[name]['entry_datetime']    = current_dt
			orderbook[name]['breaked_even']      = False



		if sc1 and sc2 and sc3 and sc4 and sc5:

			print(f"{name}  Downtrend")
			ce_name, pe_name, strike = tsl.ATM_Strike_Selection(Underlying=name, Expiry=0)
			lot_size                 = tsl.get_lot_size(pe_name)


			try:
				orderbook[name]['qty']               = lot_size*6
				orderid                              = tsl.order_placement(tradingsymbol=pe_name, exchange='NFO', quantity=lot_size, price=0, trigger_price=0,order_type='MARKET', transaction_type='BUY', trade_type='MIS')
				orderbook[name]['entry_price']       = tsl.get_ltp_data(names=[pe_name])[pe_name] # tsl.get_executed_price(orderid=orderid)
			except Exception as e:
				print(f"Error placing entry order: {e}")
				continue

			try:
				trigger_price            = round(orderbook[name]['entry_price']*0.7, 1)
				price                    = max(trigger_price - 0.5, 0.1)
				sl_orderid               = tsl.order_placement(tradingsymbol=pe_name, exchange='NFO', quantity=lot_size, price=price, trigger_price=trigger_price,order_type='STOPLIMIT', transaction_type='SELL', trade_type='MIS')
			except Exception as e:
				print(f"Error placing SL order: {e}")
				cancel_entry_order             = tsl.cancel_order(OrderID=entry_orderid)
				orderbook[name]                = {'traded':"TRADE_NOT_POSSIBLE", 'options_name':None}
				continue



			orderbook[name]['options_name']      = pe_name
			orderbook[name]['date']              = str(current_dt.date())
			orderbook[name]['entry_time']        = str(current_dt.time())
			orderbook[name]['sl_price']          = trigger_price
			orderbook[name]['tg_price']          = round(orderbook[name]['entry_price']*1.3, 1)
			orderbook[name]['buy_sell']          = 'BUY_PE'
			orderbook[name]['traded']            = True
			orderbook[name]['entry_orderid']     = orderid
			orderbook[name]['sl_orderid']         = sl_orderid
			orderbook[name]['entry_datetime']    = current_dt
			orderbook[name]['breaked_even']      = False




		if orderbook[name]['traded']:

			buy_call = orderbook[name]['buy_sell'] == 'BUY_CE'
			buy_put  = orderbook[name]['buy_sell'] == 'BUY_PE'

			if buy_call or buy_put:

				options_name    = orderbook[name]['options_name']

				options_ltp      = tsl.get_ltp_data(names=[options_name])[options_name]
				time_exit        = datetime.datetime.now() >  orderbook[name]['entry_datetime'] + datetime.timedelta(minutes=30)
				sl_hit           = options_ltp <  orderbook[name]['sl_price']
				tg_hit           = options_ltp >  orderbook[name]['tg_price']


				if buy_call:
					trailing_exit   = comp_candle['STX_15_3'] == 'down'
				if buy_put:
					trailing_exit   = comp_candle['STX_15_3'] == 'up'


				orderbook[name]['pnl']         = round((options_ltp - orderbook[name]['entry_price']) * orderbook[name]['qty'], 2)



				# Trailing Start 
				if orderbook[name]['breaked_even'] == False:
					if orderbook[name]['pnl'] > 2000:
						trigger_price     = round(orderbook[name]['entry_price'],1)
						price             = max(trigger_price - 0.5, 0.1)
						orderbook[name]['sl_price']          = trigger_price
						modified_order_id                    = tsl.modify_order(order_id=orderbook[name]['sl_orderid'],order_type="STOPLIMIT",quantity=50,price=price,trigger_price=trigger_price)
						orderbook[name]['breaked_even']      = True
						orderbook[name]['next_trailing_pnl'] = 2000 + 500


				if orderbook[name]['breaked_even']:
					if orderbook[name]['pnl'] > orderbook[name]['next_trailing_pnl']:
						
						trigger_price     = round(orderbook[name]['entry_price'] + (500/orderbook[name]['qty']),1)
						price             = max(trigger_price - 0.5, 0.1)
						orderbook[name]['sl_price']          = trigger_price

						try:
							modified_order_id = tsl.modify_order(order_id=orderbook[name]['sl_orderid'],order_type="STOPLIMIT",quantity=50,price=price,trigger_price=trigger_price)
						except Exception as e:
							print(f"Error modifying order: {e}")
							cancel_sl_order   = tsl.cancel_order(OrderID=orderbook[name]['sl_orderid'])
							sl_orderid        = tsl.order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO', quantity=orderbook[name]['qty'], price=price, trigger_price=trigger_price,order_type='STOPLIMIT', transaction_type='SELL', trade_type='MIS')
							orderbook[name]['sl_orderid'] = sl_orderid
							orderbook[name]['next_trailing_pnl'] = orderbook[name]['next_trailing_pnl'] + 500

				# Trailing End



				if trailing_exit or sl_hit:
					orderbook[name]['remark']                          = "trailing_exit" if trailing_exit else "sl_hit"
					orderbook[name]['exit_orderid'] = orderbook[name]['sl_orderid']


				if time_exit or tg_hit:
					orderbook[name]['remark']                          = "time_exit" if time_exit else "tg_hit"
					cancel_sl_order                 = tsl.cancel_order(OrderID=orderbook[name]['sl_orderid'])
					orderbook[name]['exit_orderid'] = tsl.order_placement(tradingsymbol=orderbook[name]['options_name'], exchange='NFO', quantity=orderbook[name]['qty'], price=0, trigger_price=0,order_type='MARKET', transaction_type='SELL', trade_type='MIS')


				if trailing_exit or sl_hit or time_exit or tg_hit:

					orderbook[name]['exit_price']  = tsl.get_ltp_data(names=[options_name])[options_name] # tsl.get_executed_price(orderid=orderbook[name]['exit_orderid'])
					orderbook[name]['exit_time']   = str(current_dt.time())
					orderbook[name]['pnl']         = round((orderbook[name]['exit_price'] - orderbook[name]['entry_price']) * orderbook[name]['qty'], 2)

					if re_entry:
						complted_orderbook.append(orderbook[name])						
						orderbook[name] = status.copy()



