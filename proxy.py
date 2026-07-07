from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import hashlib
import hmac
import time

app = Flask(__name__)
CORS(app, origins=["null", "http://localhost", "http://127.0.0.1"])

DELTA_BASE_URL = "https://api.india.delta.exchange"

# Your computer clock is ahead by ~708 seconds
TIME_OFFSET = -708

def get_corrected_timestamp():
    return str(int(time.time()) + TIME_OFFSET)

def generate_signature(secret, method, path, query_string, payload, timestamp):
    message       = method + timestamp + path + query_string + payload
    secret_bytes  = bytes(secret, "utf-8")
    message_bytes = bytes(message, "utf-8")
    return hmac.new(secret_bytes, message_bytes, hashlib.sha256).hexdigest()

@app.route("/proxy", methods=["POST"])
def proxy():
    try:
        data = request.get_json()
        api_key    = data.get("api_key")
        api_secret = data.get("api_secret")
        method     = data.get("method", "GET").upper()
        path       = data.get("path")
        query      = data.get("query", "")
        payload    = data.get("payload", "")

        if not api_key or not api_secret or not path:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        timestamp = get_corrected_timestamp()
        print(f"[SIGN] Corrected timestamp: {timestamp} (offset: {TIME_OFFSET}s)")

        signature = generate_signature(
            api_secret, method, path, query, payload, timestamp
        )

        headers = {
            "api-key":      api_key,
            "timestamp":    timestamp,
            "signature":    signature,
            "Content-Type": "application/json",
            "User-Agent":   "html-trading-bot"
        }

        url = DELTA_BASE_URL + path
        if query:
            url += query

        print(f"[REQUEST] {method} {url}")

        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            resp = requests.post(url, headers=headers, data=payload, timeout=10)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, data=payload, timeout=10)
        else:
            return jsonify({"success": False, "error": "Unsupported method"}), 400

        print(f"[RESPONSE] Status: {resp.status_code} | Body: {resp.text[:300]}")
        return jsonify(resp.json()), resp.status_code

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/public", methods=["GET"])
def public():
    try:
        path  = request.args.get("path")
        query = request.args.get("query", "")

        if not path:
            return jsonify({"success": False, "error": "Missing path"}), 400

        url = DELTA_BASE_URL + path
        if query:
            url += query

        print(f"[PUBLIC] GET {url}")
        resp = requests.get(url, timeout=10)
        print(f"[PUBLIC] Status: {resp.status_code}")
        return jsonify(resp.json()), resp.status_code

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    local_time     = int(time.time())
    corrected_time = local_time + TIME_OFFSET
    print("=" * 50)
    print("  Delta Exchange Local Proxy Running")
    print("  Listening on http://localhost:5000")
    print("=" * 50)
    print(f"  Local time     : {local_time}")
    print(f"  Corrected time : {corrected_time}")
    print(f"  Offset applied : {TIME_OFFSET} seconds")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)
