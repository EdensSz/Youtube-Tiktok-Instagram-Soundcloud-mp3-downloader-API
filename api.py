from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import glob
from threading import Thread
import time

app = Flask(__name__)
CORS(app)

# Stocker les fichiers téléchargés temporairement
downloads = {}

def cleanup_old_files():
    """Nettoie les fichiers de plus de 10 minutes"""
    while True:
        time.sleep(300)  # Toutes les 5 minutes
        current_time = time.time()
        to_delete = []
        
        for file_id, data in downloads.items():
            if current_time - data['timestamp'] > 600:  # 10 minutes
                try:
                    if os.path.exists(data['path']):
                        os.remove(data['path'])
                    to_delete.append(file_id)
                except:
                    pass
        
        for file_id in to_delete:
            downloads.pop(file_id, None)

# Démarrer le nettoyage en arrière-plan
Thread(target=cleanup_old_files, daemon=True).start()

@app.route('/')
def home():
    return jsonify({'message': 'API de téléchargement audio active ✅'})

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json(force=True)
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL manquante'}), 400
        
        # Créer un ID unique pour ce téléchargement
        download_id = str(uuid.uuid4())[:8]
        output_path = f'/tmp/audio_{download_id}'
        
        # Configuration yt-dlp avec options anti-blocage
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if os.path.exists('/usr/bin/ffmpeg') else [],
            'outtmpl': output_path + '.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            # Options anti-blocage YouTube
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        # Télécharger la vidéo et extraire l'audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
        
        # Trouver le fichier audio généré (n'importe quelle extension)
        audio_files = glob.glob(f'{output_path}.*')
        
        if not audio_files:
            return jsonify({'error': 'Fichier audio non généré'}), 500
        
        audio_file = audio_files[0]
        
        # Sauvegarder les infos du fichier
        downloads[download_id] = {
            'path': audio_file,
            'title': title,
            'timestamp': time.time()
        }
        
        # Retourner l'URL de téléchargement
        download_url = f'https://web-production-4bea.up.railway.app/file/{download_id}'
        
        return jsonify({
            'success': True,
            'message': 'Audio ready to download',
            'title': title,
            'download_url': download_url,
            'download_id': download_id
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Erreur: {str(e)}',
            'success': False
        }), 400

@app.route('/file/<download_id>')
def get_file(download_id):
    """Télécharge le fichier via son ID"""
    if download_id not in downloads:
        return jsonify({'error': 'File not found or expired'}), 404
    
    file_data = downloads[download_id]
    
    if not os.path.exists(file_data['path']):
        return jsonify({'error': 'File no longer available'}), 404
    
    # Détecter l'extension du fichier
    file_ext = os.path.splitext(file_data['path'])[1] or '.mp3'
    
    return send_file(
        file_data['path'],
        mimetype='audio/mpeg',
        as_attachment=True,
        download_name=f"{file_data['title']}{file_ext}"
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
