from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import ping3

app = Flask(__name__)
CORS(app)

# Global IP list
ips = ["192.168.1.1", "8.8.8.8", "127.0.0.1"]

# Language-specific messages
translations = {
    "pt": {"active": "Ativo", "inactive": "Inativo", "latency_na": "N/D"},
    "en": {"active": "Active", "inactive": "Inactive", "latency_na": "N/A"}
}

@app.route('/status', methods=['GET'])
def get_status():
    # Get the language parameter (default is 'pt' for Portuguese)
    lang = request.args.get('lang', 'pt')
    translation = translations.get(lang, translations['pt'])

    # Prepare the status response
    status = {}
    for ip in ips:
        latency = ping3.ping(ip)  # Avoid calling ping twice
        status[ip] = {
            "status": translation["active"] if latency else translation["inactive"],
            "latency": latency or translation["latency_na"]
        }
    return jsonify(status)

@app.route('/update_ips', methods=['POST'])
def update_ips():
    global ips
    data = request.get_json()
    # Add new IP
    if 'add' in data:
        ips.append(data['add'])
    # Remove IP if it exists
    if 'remove' in data and data['remove'] in ips:
        ips.remove(data['remove'])
    return jsonify({"updated_ips": ips})

@app.route('/', methods=['GET'])
def home():
    # Serve the dashboard HTML
    return render_template("monips.html")

if __name__ == '__main__':
    app.run(debug=True)
