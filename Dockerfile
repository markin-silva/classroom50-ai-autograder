FROM python:3.11-slim

WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte e os prompts
COPY src/ ./src/
COPY prompts/ ./prompts/

# Define o entrypoint. Os argumentos serão passados no momento do 'docker run'
ENTRYPOINT ["python", "src/main.py"]