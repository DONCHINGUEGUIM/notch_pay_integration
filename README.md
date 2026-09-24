# Notch Pay Gateway Tester

Flask test bench for the [Notch Pay](https://notchpay.co) API — verify keys and exercise full mobile money payment flows (collections, charges, checkout, status, transfers) before wiring them into production.

## Features

| Action | What it does |
|--------|--------------|
| **Test Auth** | Verify API credentials in one request |
| **Initialize Payment** | Create a transaction, get a payment reference |
| **Pay Now (direct charge)** | Initialize + charge in one step (mobile money) |
| **Process Payment** | Push a charge to a given channel (`cm.mtn`, `cm.orange`, …) |
| **Payment Status** | Query a transaction by reference |
| **Checkout Init** | Generate hosted checkout links |
| **Transfer** | Test withdrawals (requires private key) |

## Tech Stack

- Python 3, Flask, Requests
- Frontend served from `templates/index.html`

## Getting Started

```bash
git clone https://github.com/DONCHINGUEGUIM/notch_pay_integration.git
cd notch_pay_integration
pip install flask requests
python app.py
```

Open **http://localhost:5050**.

## Configuration

Enter keys in the UI (falls back to env defaults):

| Key | Format | Where from |
|-----|--------|------------|
| API Public Key | `pk_…` | Notch Pay dashboard — collections & status |
| API Private Key | `sk_…` | Notch Pay dashboard — transfers |
| Application Token | `test_…` / `live_…` | Sandbox or live mode |
| Mode | `test` / `live` | Notch Pay dashboard |

Optional env vars: `PORT` (default `5050`).

> **Security:** never commit real live keys. The bundled defaults are sandbox test keys for local use only — rotate anything that has ever been real.

## API Endpoints (local proxy)

All endpoints are `POST` under `/api/notch/`:

- `/test-auth` — credential check
- `/initialize-payment` — create transaction
- `/pay-now` — initialize + direct charge
- `/process-payment` — charge existing reference
- `/payment-status/<reference>` — query status
- `/transfer` — withdrawal test

## Related Docs

- `NOTCH_PAY_INTEGRATION_GUIDE.md` — architecture, auth headers, and pitfalls for Flutter + JS Worker integrations.

## Author

**Donchi Ngueguim** — [github.com/DONCHINGUEGUIM](https://github.com/DONCHINGUEGUIM)

## License

MIT
