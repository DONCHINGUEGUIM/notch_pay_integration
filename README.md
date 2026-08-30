# Notch Pay Key Tester

Test your Notch Pay API keys before implementing them in production.

## Features

- **Test Auth** - Verify your API credentials in one click
- **Initialize Payment** - Create a transaction and get a payment URL
- **Make Payment** - Test direct mobile money charges
- **Check Status** - Query transaction status by ID
- **Checkout Init** - Generate hosted checkout payment links

## Setup

```bash
pip install flask requests
python app.py
```

Open http://localhost:5050

## Credentials Needed

From your Notch Pay dashboard:
- **API Public Key** - eg. `pk_xxxxxxxx`
- **API Private Key** - eg. `sk_xxxxxxxx`
- **Application Token** - `test_xxxxx` (sandbox) or `live_xxxxx` (live)
- **Mode** - `test` or `live`
