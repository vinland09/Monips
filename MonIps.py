# ...existing code...
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import ping3
import socket
import threading
import json
import os
import logging

app = Flask(__name__)
CORS(app)

# arquivo de IPs
IPS_FILE = "ips.json"

# traduções
translations = {
    "pt": {"active": "Ativo", "inactive": "Inativo", "latency_na": "N/D"},
    "en": {"active": "Active", "inactive": "Inactive", "latency_na": "N/A"}
}

LOCK = threading.Lock()
logging.basicConfig(level=logging.INFO)


def get_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ip


def load_ips():
    """Carrega ips do arquivo; retorna valor padrão se arquivo ausente ou inválido."""
    if os.path.exists(IPS_FILE):
        try:
            with open(IPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            logging.exception("Erro ao ler ips.json")
            return []
    return ["8.8.8.8"]


def save_ips(ips):
    """Salva lista de IPs em JSON."""
    try:
        with open(IPS_FILE, "w", encoding="utf-8") as f:
            json.dump(ips, f, ensure_ascii=False, indent=2)
    except Exception:
        logging.exception("Erro ao salvar ips.json")


def is_valid_ip(ip):
    if not isinstance(ip, str):
        return False
    ip = ip.strip()
    try:
        socket.inet_aton(ip)
        return True
    except Exception:
        return False


def ping_ip(ip, translation, result_dict, high_latency_ips, max_latency_data, timeout=1):
    try:
        latency = ping3.ping(ip, timeout=timeout)
        with LOCK:
            if latency is not None:
                latency_ms = round(latency * 1000, 2)
                result_dict[ip] = {"status": translation["active"], "latency": latency_ms}
                if latency_ms > 100:
                    high_latency_ips.append(f"{ip} ({latency_ms} ms)")
                if latency_ms > max_latency_data["max_latency"]:
                    max_latency_data["max_latency"] = latency_ms
                    max_latency_data["max_latency_ip"] = ip
            else:
                result_dict[ip] = {"status": translation["inactive"], "latency": translation["latency_na"]}
    except Exception:
        with LOCK:
            result_dict[ip] = {"status": translation["inactive"], "latency": translation["latency_na"]}


@app.route('/status', methods=['GET'])
def get_status():
    lang = request.args.get('lang', 'pt')
    translation = translations.get(lang, translations['pt'])

    ips = load_ips()
    status = {}
    high_latency_ips = []
    max_latency_data = {"max_latency": 0, "max_latency_ip": None}
    threads = []

    for ip in ips:
        t = threading.Thread(target=ping_ip, args=(ip, translation, status, high_latency_ips, max_latency_data))
        t.daemon = True
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return jsonify({
        "status": status,
        "high_latency_ips": high_latency_ips,
        "max_latency_ip": max_latency_data["max_latency_ip"],
        "max_latency": max_latency_data["max_latency"] if max_latency_data["max_latency_ip"] else translation["latency_na"]
    })


@app.route('/nslookup', methods=['GET'])
def nslookup():
    host = request.args.get('host')
    if not host:
        return jsonify({"error": "Host não fornecido."}), 400
    try:
        if is_valid_ip(host):
            result = socket.gethostbyaddr(host)
            return jsonify({"hostname": result[0], "aliases": result[1], "ip_addresses": result[2]})
        else:
            ip_address = socket.gethostbyname(host)
            return jsonify({"ip_address": ip_address})
    except socket.herror:
        return jsonify({"error": "IP não possui hostname."}), 404
    except socket.gaierror:
        return jsonify({"error": "Hostname não resolvido."}), 400
    except Exception:
        logging.exception("Erro em nslookup")
        return jsonify({"error": "Erro ao resolver host."}), 500


@app.route('/update_ips', methods=['POST'])
def update_ips():
    ips = load_ips()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON inválido."}), 400

    if 'add' in data:
        ip_to_add = str(data['add']).strip()
        if not is_valid_ip(ip_to_add):
            return jsonify({"error": "IP inválido."}), 400
        if ip_to_add not in ips:
            ips.append(ip_to_add)
            save_ips(ips)
            return jsonify({"message": f"IP {ip_to_add} adicionado com sucesso.", "updated_ips": ips})
        return jsonify({"error": "IP já está na lista."}), 400

    if 'remove' in data:
        ip_to_remove = str(data['remove']).strip()
        if ip_to_remove in ips:
            ips.remove(ip_to_remove)
            save_ips(ips)
            return jsonify({"message": f"IP {ip_to_remove} removido com sucesso.", "updated_ips": ips})
        return jsonify({"error": "IP não encontrado na lista."}), 404

    if 'modify' in data:
        mod = data['modify']
        if not isinstance(mod, dict):
            return jsonify({"error": "Formato de modify inválido."}), 400
        old_ip = str(mod.get('old_ip', '')).strip()
        new_ip = str(mod.get('new_ip', '')).strip()
        if not is_valid_ip(new_ip):
            return jsonify({"error": "Novo IP inválido."}), 400
        if old_ip in ips and new_ip not in ips:
            ips[ips.index(old_ip)] = new_ip
            save_ips(ips)
            return jsonify({"message": f"IP {old_ip} modificado para {new_ip}.", "updated_ips": ips})
        return jsonify({"error": "IP inválido ou já existente."}), 400

    return jsonify({"error": "Ação inválida."}), 400


@app.route('/', methods=['GET'])
def home():
    lang = request.args.get('lang', 'pt')
    ips = load_ips()
    ip_hostnames = [(ip, get_hostname(ip)) for ip in ips]
    return render_template("monips.html", ips=ips, ip_hostnames=ip_hostnames, lang=lang)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
#