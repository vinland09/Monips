from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import ping3

app = Flask(__name__)
CORS(app)

# Lista global de IPs monitorados
ips = ["192.168.1.1", "8.8.8.8", "127.0.0.1"]

# Mensagens específicas de idioma
translations = {
    "pt": {"active": "Ativo", "inactive": "Inativo", "latency_na": "N/D"},
    "en": {"active": "Active", "inactive": "Inactive", "latency_na": "N/A"}
}

@app.route('/status', methods=['GET'])
def get_status():
    # Obtém o idioma da requisição (padrão é 'pt' para português)
    lang = request.args.get('lang', 'pt')
    translation = translations.get(lang, translations['pt'])

    # Preparar os dados de status
    status = {}
    high_latency_ips = []
    max_latency = 0
    max_latency_ip = None

    for ip in ips:
        try:
            latency = ping3.ping(ip)
            if latency:
                latency_ms = round(latency * 1000, 2)  # Converte para ms
                status[ip] = {
                    "status": translation["active"],
                    "latency": latency_ms
                }
                if latency_ms > 100:  # Exemplo de limite para alta latência
                    high_latency_ips.append(f"{ip} ({latency_ms} ms)")
                if latency_ms > max_latency:
                    max_latency = latency_ms
                    max_latency_ip = ip
            else:
                status[ip] = {
                    "status": translation["inactive"],
                    "latency": translation["latency_na"]
                }
        except Exception:
            status[ip] = {
                "status": translation["inactive"],
                "latency": translation["latency_na"]
            }

    return jsonify({
        "status": status,
        "high_latency_ips": high_latency_ips,
        "max_latency_ip": max_latency_ip,
        "max_latency": max_latency if max_latency_ip else translation["latency_na"]
    })

@app.route('/update_ips', methods=['POST'])
def update_ips():
    global ips
    data = request.get_json()
    # Adicionar um novo IP
    if 'add' in data:
        ip_to_add = data['add']
        if ip_to_add not in ips:  # Evitar duplicados
            ips.append(ip_to_add)
            return jsonify({"message": f"IP {ip_to_add} adicionado com sucesso.", "updated_ips": ips})
        else:
            return jsonify({"error": "IP já está na lista."}), 400

    # Remover um IP existente
    if 'remove' in data:
        ip_to_remove = data['remove']
        if ip_to_remove in ips:
            ips.remove(ip_to_remove)
            return jsonify({"message": f"IP {ip_to_remove} removido com sucesso.", "updated_ips": ips})
        else:
            return jsonify({"error": "IP não encontrado na lista."}), 404

    # Modificar um IP existente
    if 'modify' in data:
        old_ip = data['modify'].get('old_ip')
        new_ip = data['modify'].get('new_ip')
        if old_ip in ips and new_ip not in ips:
            ips[ips.index(old_ip)] = new_ip
            return jsonify({"message": f"IP {old_ip} modificado para {new_ip}.", "updated_ips": ips})
        else:
            return jsonify({"error": "IP inválido ou já existente."}), 400

    return jsonify({"error": "Ação inválida."}), 400

@app.route('/', methods=['GET'])
def home():
    # Renderiza o dashboard HTML
    return render_template("monips.html")

if __name__ == '__main__':
    app.run(debug=True)
