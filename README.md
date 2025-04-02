Aqui está a **documentação do código Flask** fornecido. Abaixo está uma explicação detalhada de cada componente, rota, e como o código funciona:

---

### **1. Introdução**
Este código cria um **Dashboard de Monitoramento de IPs** usando o Flask. Ele inclui as seguintes funcionalidades:
- Monitoramento de uma lista de IPs e seus status (ativo/inativo).
- Relatórios de IPs com alta latência.
- Alterações dinâmicas na lista de IPs (adicionar, remover ou modificar).
- Integração com um front-end (HTML).

---

### **2. Dependências**
Certifique-se de que as bibliotecas necessárias estão instaladas:
- **Flask:** Framework web.
- **Flask-CORS:** Para evitar problemas de CORS ao integrar com o front-end.
- **ping3:** Para realizar "ping" nos IPs e medir latências.

Instale as dependências:
```bash
pip install flask flask-cors ping3
```

---

### **3. Estrutura do Código**

#### **3.1. Configurações Iniciais**
```python
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import ping3
```
- `Flask`: Cria o servidor web.
- `CORS`: Resolve problemas de **Cross-Origin Resource Sharing**.
- `ping3`: Realiza testes de ping para medir latências.

#### **3.2. Lista de IPs**
```python
ips = ["192.168.1.1", "8.8.8.8", "127.0.0.1"]
```
- Lista global de IPs para monitoramento.

#### **3.3. Traduções**
```python
translations = {
    "pt": {"active": "Ativo", "inactive": "Inativo", "latency_na": "N/D"},
    "en": {"active": "Active", "inactive": "Inactive", "latency_na": "N/A"}
}
```
- Mensagens traduzidas para os idiomas suportados: Português (`pt`) e Inglês (`en`).

---

### **4. Rotas**

#### **4.1. Rota `/status`**
- Método: **GET**
- Descrição: Retorna o status de todos os IPs monitorados.
- URL de exemplo: `http://127.0.0.1:5000/status?lang=pt`
- Código:
```python
@app.route('/status', methods=['GET'])
def get_status():
    # Obtém o idioma da requisição (default: pt)
    lang = request.args.get('lang', 'pt')
    translation = translations.get(lang, translations['pt'])

    status = {}
    high_latency_ips = []
    max_latency = 0
    max_latency_ip = None

    # Realiza ping em cada IP
    for ip in ips:
        try:
            latency = ping3.ping(ip)  # Realiza o ping
            if latency:
                latency_ms = round(latency * 1000, 2)  # Converte para ms
                status[ip] = {
                    "status": translation["active"],
                    "latency": latency_ms
                }
                if latency_ms > 100:  # Alerta de alta latência
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
```

**Resposta Exemplo (JSON):**
```json
{
    "status": {
        "192.168.1.1": {"status": "Ativo", "latency": 42.34},
        "8.8.8.8": {"status": "Ativo", "latency": 120.56},
        "127.0.0.1": {"status": "Inativo", "latency": "N/D"}
    },
    "high_latency_ips": ["8.8.8.8 (120.56 ms)"],
    "max_latency_ip": "8.8.8.8",
    "max_latency": 120.56
}
```

---

#### **4.2. Rota `/update_ips`**
- Método: **POST**
- Descrição: Permite modificar a lista de IPs (adicionar, remover ou atualizar).
- Código:
```python
@app.route('/update_ips', methods=['POST'])
def update_ips():
    global ips
    data = request.get_json()

    # Adicionar um novo IP
    if 'add' in data:
        ip_to_add = data['add']
        if ip_to_add not in ips:
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
```

**Exemplo:**
1. Adicionar um IP:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"add": "192.168.0.10"}' http://127.0.0.1:5000/update_ips
   ```

2. Remover um IP:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"remove": "8.8.8.8"}' http://127.0.0.1:5000/update_ips
   ```

3. Modificar um IP:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"modify": {"old_ip": "127.0.0.1", "new_ip": "192.168.0.20"}}' http://127.0.0.1:5000/update_ips
   ```

**Resposta Exemplo (JSON):**
```json
{"message": "IP 127.0.0.1 modificado para 192.168.0.20.", "updated_ips": ["192.168.1.1", "8.8.8.8", "192.168.0.20"]}
```

---

#### **4.3. Rota `/`**
- Método: **GET**
- Descrição: Renderiza o arquivo `monips.html`, que é a interface do usuário.
- Código:
```python
@app.route('/', methods=['GET'])
def home():
    return render_template("monips.html")
```

---

### **5. Execução**
- Execute o servidor:
```bash
python app.py
```
- Acesse no navegador: `http://127.0.0.1:5000/`.

---

### **6. Melhorias Sugestivas**
1. **Validação de IPs:**
   - Use validação adicional para aceitar somente IPs no formato correto (pode ser incluído com Regex).
2. **Persistência de Dados:**
   - Armazene a lista de IPs em um arquivo ou banco de dados para manter os dados após reiniciar o servidor.

Se precisar de mais explicações ou ajustes, é só avisar! 🚀✨
