# Notch Pay Integration Guide — Flutter + JS Worker

> Lessons learned from integrating Notch Pay collections (deposits) and transfers (withdrawals).
> Use this guide to avoid the same pitfalls when migrating to a Flutter mobile app with a JS worker.

---

## 1. Architecture

```
Flutter App  ──→  JS Worker (WebView / dart:js)  ──→  Your Backend Server  ──→  Notch Pay API
```

- **JS Worker**: Runs the Notch Pay JavaScript SDK or raw fetch calls inside a WebView/isolate.
- **Backend Server**: Proxies requests to Notch Pay (keeps API keys secure, never expose them client-side).
- **Notch Pay API**: `https://api.notchpay.co`

---

## 2. Authentication

### Two Keys

| Key | Format | Purpose | Header |
|-----|--------|---------|--------|
| **Public Key** | `pk.xxxxxxxx` | Collections & status checks | `Authorization` (raw, no "Bearer") |
| **Private Key** | `sk.xxxxxxxx` | Transfers (withdrawals) | `X-Grant` |

### ❌ Mistake we made
Adding `"Bearer "` prefix to the Public Key → got `401 Unauthorized`.

### ✅ Correct
```javascript
headers: {
  "Authorization": "pk.XR9dxcK0b1omAMwvnyBpx4bCXDUOIqhTHu3eB0T9cS321S364Yw5Aole9EtYXhTnbQipDZZln0ZoODy8hOAKLpsqGTYkiGTMTCsUDhCcYQf66FM0Ue138kwqYuexk",
  "Content-Type": "application/json"
}
```

---

## 3. Collections (Deposits) — Two-Step Flow

### Step 1: Initialize Payment

```
POST /payments
```

```javascript
const initPayload = {
  amount: 100,
  currency: "XAF",
  email: "customer@example.com",
  phone: "+237670000000",      // must have country code
  name: "John Doe",
  reference: "REF_YOUR_ID",    // your merchant reference
  description: "Order #123"
};

const resp = await fetch("https://api.notchpay.co/payments", {
  method: "POST",
  headers: {
    "Authorization": "YOUR_PUBLIC_KEY",
    "Content-Type": "application/json"
  },
  body: JSON.stringify(initPayload)
});

const data = await resp.json();
// data.transaction.reference = "trx.xxxxxxxxxxxx"  ← NOT the REF_ you sent
```

### Step 2: Process Direct Charge

```
POST /payments/{trx_reference}
```

```javascript
const processPayload = {
  channel: "cm.mtn",           // or "cm.orange"
  data: {
    phone: "+237670000000"
  }
};

const resp = await fetch(`https://api.notchpay.co/payments/${trxReference}`, {
  method: "POST",
  headers: {
    "Authorization": "YOUR_PUBLIC_KEY",
    "Content-Type": "application/json"
  },
  body: JSON.stringify(processPayload)
});
// Returns 202 Accepted on success
```

### ❌ ❌ ❌ Critical Mistake (cost us hours)
We sent `REF_123456` (our merchant reference) to the process endpoint instead of `trx.xxxxxxxx`.
**The process endpoint ONLY accepts the Notch Pay `trx.*` reference**, not your merchant `REF_*`.

### ✅ Correct
Always use `data.transaction.reference` (the `trx.*` value) from the initialize response when calling the process endpoint.

```javascript
const trxReference = data.transaction.reference;  // ← "trx.xxx" NOT "REF_xxx"
```

### One-Button Flow (Recommended)
To avoid confusion, chain both steps server-side:

```javascript
async function payNow(amount, phone, channel) {
  // Step 1: Initialize
  const init = await fetch("https://api.notchpay.co/payments", { ... });
  const initData = await init.json();
  const trxRef = initData.transaction.reference;

  // Step 2: Process immediately
  const process = await fetch(`https://api.notchpay.co/payments/${trxRef}`, { ... });
  return await process.json();
}
```

---

## 4. Important Parameters

### Phone Number Format
- Always include country code: `+237` for Cameroon
- Input: `670000000` → Format to: `+237670000000`

### Channel Codes
| Channel | Provider | Country |
|---------|----------|---------|
| `cm.mtn` | MTN Mobile Money | Cameroon |
| `cm.orange` | Orange Money | Cameroon |
| `cm.mobile` | Auto-detect (MTN/Orange) | Cameroon |
| `ci.mtn` | MTN | Côte d'Ivoire |
| `ci.orange` | Orange | Côte d'Ivoire |
| `sn.wave` | Wave | Senegal |
| `ke.mpesa` | M-Pesa | Kenya |

**Must specify channel manually** — there is no auto-detection by phone number.

### Minimum Amounts
- **Collections**: No minimum observed (tested 10 XAF)
- **Transfers**: Minimum **500 XAF**

---

## 5. Transfers (Withdrawals)

```
POST /transfers
```

```javascript
const transferPayload = {
  amount: 1000,
  currency: "XAF",
  beneficiary_data: {
    name: "Jane Doe",
    phone: "+237670000000",
    email: "beneficiary@example.com"
  },
  channel: "cm.orange",
  description: "Withdrawal",
  reference: "TRF_YOUR_REF"
};

const resp = await fetch("https://api.notchpay.co/transfers", {
  method: "POST",
  headers: {
    "Authorization": "YOUR_PUBLIC_KEY",
    "X-Grant": "YOUR_PRIVATE_KEY",      // ← REQUIRED for transfers
    "Content-Type": "application/json"
  },
  body: JSON.stringify(transferPayload)
});
```

### ❌ Mistake we made
Calling transfers without the `X-Grant` header → got `403 Forbidden`.

### IP Whitelisting
Transfers require the server IP to be whitelisted:
1. Go to `https://business.notchpay.co/settings/developer/ips`
2. Add your server's public IP address

### ❌ Mistake we made
Tried transfers before whitelisting the IP → got `403 IP address not allowed`.

### Fee Structure
| Operation | Fee |
|-----------|-----|
| Collections (deposits) | **2%** per payment |
| Transfers (withdrawals) | **1%** per transfer |
| Setup / Monthly | **Free** |

---

## 6. Common Errors & Solutions

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Wrong key format or "Bearer" prefix | Send raw key without "Bearer" |
| `404 Payment Not Found` | Using `REF_*` instead of `trx.*` on process endpoint | Use `data.transaction.reference` from initialize |
| `403 IP address not allowed` | IP not whitelisted for transfers | Add server IP in dashboard |
| `403 Forbidden` (transfers) | Missing `X-Grant` header | Add Private Key as `X-Grant` |
| `422 Invalid CM Orange Money` | Phone doesn't match the channel | Use MTN number (`+23767...`) for `cm.mtn`, Orange (`+23769...`) for `cm.orange` |
| `422 amount must be >= 500` | Transfer below minimum | Send ≥ 500 XAF |
| `500 Whoop's Application Error` | Transient Notch Pay server error | Retry after a few seconds |
| Timeout (read timeout) | Slow network or Notch Pay latency | Increase timeout to ≥ 30s |

---

## 7. Flutter + JS Worker Implementation Tips

### Architecture Options

**Option A: WebView JS Worker**
```dart
// Flutter side
final jsBridge = JavaScriptChannel(name: 'NotchBridge');
webViewController.addJavaScriptChannel(jsBridge);

// JS side (in WebView)
async function processPayment(amount, phone, channel) {
  const result = await fetch('/api/notch/pay-now', { ... });
  NotchBridge.postMessage(JSON.stringify(result));
}
```

**Option B: Direct HTTP from Dart (Simpler)**
```dart
// Skip the JS worker entirely, call your backend directly
final response = await http.post(
  Uri.parse('$backendUrl/api/notch/pay-now'),
  body: { amount: 100, phone: '+237670000000', channel: 'cm.mtn' }
);
```

### Security Rules
1. **NEVER** embed Public/Private keys in Flutter app code
2. Always proxy through your backend server
3. Use HTTPS for all API calls
4. Validate phone numbers server-side

### JS Worker Gotchas
- WebView CORS policies may block direct Notch Pay API calls
- Use your backend as a proxy (Flask endpoint calls Notch Pay)
- Handle timeout errors gracefully in the JS ↔ Dart bridge

---

## 8. Quick Reference — Endpoints Summary

| Action | Method | Endpoint | Auth | Notes |
|--------|--------|----------|------|-------|
| Initialize | `POST` | `/payments` | Public Key | Returns `trx.*` ref |
| Process | `POST` | `/payments/{trx_ref}` | Public Key | Use `trx.*` not `REF_*` |
| Check Status | `GET` | `/payments/{ref}` | Public Key | Works with either ref |
| List Payments | `GET` | `/payments` | Public Key | Paginated |
| Transfer | `POST` | `/transfers` | Public + Private | Requires IP whitelist |

Base URL: `https://api.notchpay.co`

---

## 9. Recommended Backend Structure (your Flask app)

Keep the combined `pay-now` endpoint that does initialize + process in one call:

```
POST /api/notch/pay-now
  Body: { amount, currency, phone, channel }
  Returns: { step: "process", status_code, response, _trx_ref, _merchant_ref }
```

Your Flutter app only needs to call this one endpoint for collections.

---

*Generated from real debugging sessions with the Notch Pay API (July 2026)*
