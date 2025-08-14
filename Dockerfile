# Usar uma imagem base do Python
FROM python:3.9-slim

# Definir o diretório de trabalho no container
WORKDIR /app

# Copiar os arquivos do projeto para o container
COPY . /app

# Instalar as dependências do projeto
RUN pip install --no-cache-dir flask flask-cors ping3

# Expor a porta 5000
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "MonIps.py"]