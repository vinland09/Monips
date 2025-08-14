from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import ping3
import socket
import threading
import json
import os

app = Flask(__name__)
CORS(app)

# Caminho para persistência dos IPs monitorados
IPS_FILE = "ips.json"

# Mensagens específicas de idioma
translations = {
    "pt": {"active": "Ativo", "inactive": "Inativo", "latency_na": "N/D"},
    "en": {"active": "Active", "inactive": "Inactive", "latency_na": "N/A"}
}

def get_hostname(ip):
    """Tenta obter o hostname de um IP. Retorna o IP se não conseguir resolver."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ip

def load_ips():
    """Carrega a lista de IPs monitorados do arquivo JSON."""
    if os.path.exists(IPS_FILE):
        try:
            with open(IPS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Valor padrão se não existir arquivo
    return ["8.8.8.8",]

def save_ips(ips):
    """Salva a lista de IPs monitorados no arquivo JSON."""
    with open(IPS_FILE, "w") as f:
        json.dump(ips, f)

def is_valid_ip(ip):
    """Valida se o IP fornecido é válido."""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def ping_ip(ip, translation, result_dict, high_latency_ips, max_latency_data):
    """Executa o ping em um IP e armazena o resultado em result_dict."""
    try:
        latency = ping3.ping(ip)
        if latency:
            latency_ms = round(latency * 1000, 2)
            result_dict[ip] = {
                "status": translation["active"],
                "latency": latency_ms
            }
            if latency_ms > 100:
                high_latency_ips.append(f"{ip} ({latency_ms} ms)")
            with threading.Lock():
                if latency_ms > max_latency_data["max_latency"]:
                    max_latency_data["max_latency"] = latency_ms
                    max_latency_data["max_latency_ip"] = ip
        else:
            result_dict[ip] = {
                "status": translation["inactive"],
                "latency": translation["latency_na"]
            }
    except Exception:
        result_dict[ip] = {
            "status": translation["inactive"],
            "latency": translation["latency_na"]
        }

@app.route('/status', methods=['GET'])
def get_status():
    """
    Retorna o status (ativo/inativo) e latência dos IPs monitorados.
    Também retorna IPs com alta latência e o IP com maior latência.
    Agora faz ping em paralelo para melhor desempenho.
    """
    lang = request.args.get('lang', 'pt')
    translation = translations.get(lang, translations['pt'])

    ips = load_ips()
    status = {}
    high_latency_ips = []
    max_latency_data = {"max_latency": 0, "max_latency_ip": None}
    threads = []

    # Executa pings em paralelo
    for ip in ips:
        t = threading.Thread(target=ping_ip, args=(ip, translation, status, high_latency_ips, max_latency_data))
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
    """
    Realiza uma consulta DNS reversa (nslookup) para um host ou IP.
    Retorna hostname, aliases e IPs, ou apenas o IP se for hostname.
    """
    host = request.args.get('host')
    if not host:
        return jsonify({"error": "Host não fornecido."}), 400

    try:
        if is_valid_ip(host):
            result = socket.gethostbyaddr(host)
            return jsonify({
                "hostname": result[0],
                "aliases": result[1],
                "ip_addresses": result[2]
            })
        else:
            ip_address = socket.gethostbyname(host)
            return jsonify({"ip_address": ip_address})
    except socket.herror:
        return jsonify({"error": "IP não possui hostname."}), 404
    except socket.gaierror:
        return jsonify({"error": "Hostname não resolvido."}), 400

@app.route('/update_ips', methods=['POST'])
def update_ips():
    """
    Permite adicionar, remover ou modificar IPs monitorados via POST.
    Espera um JSON com as chaves: add, remove ou modify.
    Agora persiste as alterações em disco.
    """
    ips = load_ips()
    data = request.get_json()
    # Adicionar um novo IP
    if 'add' in data:
        ip_to_add = data['add']
        if not is_valid_ip(ip_to_add):
            return jsonify({"error": "IP inválido."}), 400
        if ip_to_add not in ips:
            ips.append(ip_to_add)
            save_ips(ips)
            return jsonify({"message": f"IP {ip_to_add} adicionado com sucesso.", "updated_ips": ips})
        else:
            return jsonify({"error": "IP já está na lista."}), 400

    # Remover um IP existente
    if 'remove' in data:
        ip_to_remove = data['remove']
        if ip_to_remove in ips:
            ips.remove(ip_to_remove)
            save_ips(ips)
            return jsonify({"message": f"IP {ip_to_remove} removido com sucesso.", "updated_ips": ips})
        else:
            return jsonify({"error": "IP não encontrado na lista."}), 404

    # Modificar um IP existente
    if 'modify' in data:
        old_ip = data['modify'].get('old_ip')
        new_ip = data['modify'].get('new_ip')
        if not is_valid_ip(new_ip):
            return jsonify({"error": "Novo IP inválido."}), 400
        if old_ip in ips and new_ip not in ips:
            ips[ips.index(old_ip)] = new_ip
            save_ips(ips)
            return jsonify({"message": f"IP {old_ip} modificado para {new_ip}.", "updated_ips": ips})
        else:
            return jsonify({"error": "IP inválido ou já existente."}), 400

    return jsonify({"error": "Ação inválida."}), 400

@app.route('/', methods=['GET'])
def home():
    """
    Renderiza o dashboard HTML principal (monips.html).
    Agora envia a lista de IPs e hostnames para o template.
    """
    lang = request.args.get('lang', 'pt')
    ips = load_ips()
    ip_hostnames = [(ip, get_hostname(ip)) for ip in ips]
    return render_template("monips.html", ips=ips, ip_hostnames=ip_hostnames, lang=lang)

if __name__ == "__main__":
    # Inicia o servidor Flask na porta 5000
    app.run(host="0.0.0.0", port=5000, debug=True)