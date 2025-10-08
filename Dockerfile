FROM python:3.11-slim

# Installer FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copier les fichiers
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Démarrer l'application
CMD gunicorn api:app --bind 0.0.0.0:$PORT
