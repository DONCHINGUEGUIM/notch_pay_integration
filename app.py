import os, uuid
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DEFAULT_BASE_URL = "https://api.notchpay.co"
DEFAULT_PUBLIC_KEY = "pk_test.K9KSdd2QmG82UYLpbBa2SjkptJqO53GGQJxuJWvqhBiBKfEGLj0vElN7wJrvZJs8mnDdliJ2e4lxBHwHQxL6ZHDAzWWM8XT8MQ9uJRmQ9yD4kcAc01GHlhHAAG7sH"
DEFAULT_PRIVATE_KEY = "sk_test.IKlL3l6xvo1iWxP4hQpanF8knuUN2r06NJZwXaxXoz3iFVNfNMHsDSIUEslPyarSQhKQy959v5nbwcAhRFphTtaAFIKDb0UkSpqmpbjMP7monA2DdpKeOtiFgT5JT"


def _headers(api_key, private_key=None):
    h = {
        "Authorization": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if private_key:
        h["X-Grant"] = private_key
    return h


def _get_keys(data):
    return (
        data.get('api_key') or DEFAULT_PUBLIC_KEY,
        data.get('private_key') or DEFAULT_PRIVATE_KEY,
        data.get('base_url', DEFAULT_BASE_URL).rstrip('/')
    )


def _fmt_phone(phone):
    if not phone.startswith('+'):
        return '+237' + phone.lstrip('0')
    return phone


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/notch/test-auth', methods=['POST'])
def test_auth():
    data = request.json or {}
    api_key, _, base_url = _get_keys(data)
    try:
        resp = requests.get(f"{base_url}/payments", headers=_headers(api_key), timeout=10)
        return jsonify({"status_code": resp.status_code, "response": resp.json() if resp.content else resp.text})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route('/api/notch/pay-now', methods=['POST'])
def pay_now():
    data = request.json or {}
    api_key, private_key, base_url = _get_keys(data)
    phone = _fmt_phone(data.get('phone', '670000000'))
    channel = data.get('channel', 'cm.mtn')
    amount = float(data.get('amount', 100))
    currency = data.get('currency', 'XAF')
    ref = data.get('reference', 'REF_' + str(uuid.uuid4()).replace('-', '')[:8])

    # Step 1: Initialize payment
    init_payload = {
        "amount": amount,
        "currency": currency,
        "email": data.get('email', 'customer@example.com'),
        "phone": phone,
        "name": data.get('name', 'Test User'),
        "reference": ref,
        "description": data.get('description', 'Test Payment')
    }
    try:
        init_resp = requests.post(f"{base_url}/payments", json=init_payload, headers=_headers(api_key), timeout=60)
        init_data = init_resp.json() if init_resp.content else {}
        if init_resp.status_code not in (200, 201):
            return jsonify({"step": "initialize", "status_code": init_resp.status_code, "response": init_data})
    except Exception as e:
        return jsonify({"step": "initialize", "status": "ERROR", "message": str(e)}), 500

    trx_ref = (init_data.get('transaction') or {}).get('reference')
    if not trx_ref:
        return jsonify({"step": "initialize", "status": "ERROR", "message": "No transaction reference returned", "response": init_data})

    # Step 2: Process direct charge
    process_payload = {
        "channel": channel,
        "data": {"phone": phone}
    }
    try:
        proc_resp = requests.post(f"{base_url}/payments/{trx_ref}", json=process_payload, headers=_headers(api_key), timeout=30)
        proc_data = proc_resp.json() if proc_resp.content else {}
        return jsonify({
            "step": "process",
            "status_code": proc_resp.status_code,
            "response": proc_data,
            "_trx_ref": trx_ref,
            "_merchant_ref": ref
        })
    except Exception as e:
        return jsonify({"step": "process", "error": str(e), "_trx_ref": trx_ref})


@app.route('/api/notch/initialize-payment', methods=['POST'])
def initialize_payment():
    data = request.json or {}
    api_key, private_key, base_url = _get_keys(data)
    ref = data.get('reference', 'REF_' + str(uuid.uuid4()).replace('-', '')[:8])
    payload = {
        "amount": float(data.get('amount', 100)),
        "currency": data.get('currency', 'XAF'),
        "email": data.get('email', 'customer@example.com'),
        "phone": _fmt_phone(data.get('phone', '670000000')),
        "name": data.get('name', 'Test User'),
        "reference": ref,
        "description": data.get('description', 'Test Payment')
    }
    try:
        resp = requests.post(f"{base_url}/payments", json=payload, headers=_headers(api_key, private_key), timeout=15)
        result = resp.json() if resp.content else resp.text
        extra = {}
        if isinstance(result, dict):
            t = result.get('transaction', {})
            extra['_notch_ref'] = t.get('reference')
            extra['_merchant_ref'] = t.get('merchant_reference')
        return jsonify({"status_code": resp.status_code, "response": result, **extra})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route('/api/notch/process-payment', methods=['POST'])
def process_payment():
    data = request.json or {}
    api_key, private_key, base_url = _get_keys(data)
    reference = data.get('reference')
    if not reference:
        return jsonify({"status": "ERROR", "message": "Reference required"}), 400
    payload = {
        "channel": data.get('channel', 'cm.mtn'),
        "data": {"phone": _fmt_phone(data.get('phone', '670000000'))}
    }
    try:
        resp = requests.post(f"{base_url}/payments/{reference}", json=payload, headers=_headers(api_key, private_key), timeout=30)
        return jsonify({"status_code": resp.status_code, "response": resp.json() if resp.content else resp.text})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route('/api/notch/payment-status/<reference>', methods=['POST'])
def payment_status(reference):
    api_key, _, base_url = _get_keys(request.json or {})
    try:
        resp = requests.get(f"{base_url}/payments/{reference}", headers=_headers(api_key), timeout=15)
        return jsonify({"status_code": resp.status_code, "response": resp.json() if resp.content else resp.text})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


@app.route('/api/notch/transfer', methods=['POST'])
def transfer():
    data = request.json or {}
    api_key, private_key, base_url = _get_keys(data)
    if not private_key:
        return jsonify({"status": "ERROR", "message": "Private Key required for transfers"}), 400
    payload = {
        "amount": float(data.get('amount', 1000)),
        "currency": data.get('currency', 'XAF'),
        "beneficiary": {
            "name": data.get('beneficiary_name', 'Test Beneficiary'),
            "phone": _fmt_phone(data.get('beneficiary_phone', '670000000')),
            "email": data.get('beneficiary_email', 'beneficiary@example.com')
        },
        "channel": data.get('channel', 'cm.orange'),
        "description": data.get('description', 'Withdrawal'),
        "reference": data.get('reference', 'TRF_' + str(uuid.uuid4()).replace('-', '')[:12])
    }
    try:
        resp = requests.post(f"{base_url}/transfers", json=payload, headers=_headers(api_key, private_key), timeout=15)
        return jsonify({"status_code": resp.status_code, "response": resp.json() if resp.content else resp.text})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port)
