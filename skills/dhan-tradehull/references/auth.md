# Auth — Output Signatures

## `Tradehull(client_code, token_id, mode="access_token")`

**Version:** 3.3.1
```python
tsl = Tradehull(client_code, token_id, mode="access_token")
```

**Console output on success:**
```
Attempting authentication using ACCESS TOKEN.
Input access token profile validated successfully
Token validity: 28/06/2026 07:52
System is fetching the latest instrument file from Dhan
Instrument file retrieved successfully
-----SUCCESSFULLY LOGGED INTO DHAN-----
```

**Return type:** `Dhan_Tradehull.Dhan_Tradehull.Tradehull` object
```python
>>> tsl
<Dhan_Tradehull.Dhan_Tradehull.Tradehull object at 0x000001BE902D96D0>
```

**Auth mode comparison:**

| Mode | Validity | Best For |
|------|----------|----------|
| `access_token` | ⚠️ Daily — regenerate every morning | Manual/semi-auto |
| `api_key` | Browser flow each time | One-off scripts |
| `pin_totp` | ✅ Lifetime — PIN never expires | Fully automated algos |

**Notes:**
- Token validity shown as `DD/MM/YYYY HH:MM`
- Instrument file auto-fetched on every login
- Memory address differs every run — normal
- ⚠️ `access_token`: regenerate daily from Dhan web → My Profile → API Access
- ✅ `pin_totp`: PIN valid for lifetime — preferred for scheduled/automated algos
