# Obtenir la taille du fichier
        file_size = os.path.getsize(audio_file)
        
        # Envoyer le fichier à Bubble via le Backend Workflow
        try:
            with open(audio_file, 'rb') as f:
                files = {
                    'audio_file': (f'{title}.mp3', f, 'audio/mpeg')
                }
                data = {
                    'title': title,
                    'duration': duration
                }
                
                bubble_response = requests.post(
                    BUBBLE_WORKFLOW_URL,
                    files=files,
                    data=data,
                    timeout=60
                )
                
                if bubble_response.status_code != 200:
                    return jsonify({
                        'error': f'Erreur lors de l\'upload vers Bubble: {bubble_response.text}',
                        'success': False
                    }), 500
        
        except Exception as upload_error:
            return jsonify({
                'error': f'Erreur upload Bubble: {str(upload_errorfrom flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import glob
from threading import Thread
import time
import requests

app = Flask(__name__)
CORS(app)

# URL du Backend Workflow Bubble - CHANGE ÇA !
BUBBLE_WORKFLOW_URL = "https://TON_APP.bubbleapps.io/version-test/api/1.1/wf/receive_audio"

# Stocker les fichiers téléchargés temporairement
downloads = {}

def cleanup_old_files():
    """Nettoie les fichiers de plus de 7 jours"""
    while True:
        time.sleep(3600)  # Toutes les heures
        current_time = time.time()
        to_delete = []
        
        for file_id, data in downloads.items():
            if current_time - data['timestamp'] > 604800:  # 7 jours
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
        
        # Vérifier si FFmpeg est disponible
        has_ffmpeg = os.path.exists('/usr/bin/ffmpeg') or os.system('which ffmpeg') == 0
        
        # Configuration yt-dlp avec options anti-blocage RENFORCÉES
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if has_ffmpeg else [],
            'outtmpl': output_path + '.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            # Options anti-blocage YouTube RENFORCÉES
            'nocheckcertificate': True,
            'geo_bypass': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios'],
                    'player_skip': ['webpage', 'configs'],
                    'skip': ['dash', 'hls']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }
        
        # Télécharger la vidéo et extraire l'audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
            duration = info.get('duration', 0)
        
        # Trouver le fichier audio généré
        if has_ffmpeg:
            audio_file = f'{output_path}.mp3'
            if not os.path.exists(audio_file):
                audio_files = glob.glob(f'{output_path}*.mp3')
                if audio_files:
                    audio_file = audio_files[0]
                else:
                    return jsonify({'error': 'Fichier MP3 non généré'}), 500
        else:
            audio_files = glob.glob(f'{output_path}.*')
            if not audio_files:
                return jsonify({'error': 'Fichier audio non généré'}), 500
            audio_file = audio_files[0]
        
        # Obtenir la taille du fichier
        file_size = os.path.getsize(audio_file)
        
        # Sauvegarder les infos du fichier
        downloads[download_id] = {
            'path': audio_file,
            'title': title,
            'duration': duration,
            'size': file_size,
            'timestamp': time.time(),
            'has_ffmpeg': has_ffmpeg
        }
        
        # Retourner l'URL de téléchargement avec extension .mp3
        file_url = f'https://web-production-4bea.up.railway.app/file/{download_id}.mp3'
        
        return jsonify({
            'success': True,
            'message': 'Audio ready',
            'title': title,
            'file_url': file_url,
            'download_id': download_id,
            'duration': duration,
            'file_size': file_size,
            'format': 'mp3' if has_ffmpeg else 'original',
            'ffmpeg_installed': has_ffmpeg
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Erreur: {str(e)}',
            'success': False
        }), 400

@app.route('/file/<path:filename>')
def get_file(filename):
    """Télécharge le fichier via son ID (avec ou sans extension)"""
    # Retirer l'extension .mp3 si présente
    download_id = filename.replace('.mp3', '').replace('.m4a', '').replace('.webm', '')
    
    if download_id not in downloads:
        return jsonify({'error': 'File not found or expired'}), 404
    
    file_data = downloads[download_id]
    
    if not os.path.exists(file_data['path']):
        return jsonify({'error': 'File no longer available'}), 404
    
    # Déterminer l'extension et le mime type
    file_ext = os.path.splitext(file_data['path'])[1] or '.mp3'
    
    # Nettoyer le titre pour le nom de fichier
    safe_title = "".join(c for c in file_data['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title[:100]  # Limiter la longueur
    
    return send_file(
        file_data['path'],
        mimetype='audio/mpeg',
        as_attachment=False  # False = streamable, True = téléchargement forcé
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
