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

downloads = {}

def cleanup_old_files():
    """Nettoie les fichiers de plus de 7 jours"""
    while True:
        time.sleep(3600)
        current_time = time.time()
        to_delete = []
        
        for file_id, data in downloads.items():
            if current_time - data.get('timestamp', 0) > 604800:
                try:
                    if data.get('path') and os.path.exists(data['path']):
                        os.remove(data['path'])
                    to_delete.append(file_id)
                except:
                    pass
        
        for file_id in to_delete:
            downloads.pop(file_id, None)

Thread(target=cleanup_old_files, daemon=True).start()

@app.route('/')
def home():
    return jsonify({'message': 'API de téléchargement audio active ✅'})

@app.route('/download', methods=['POST'])
def download():
    """Télécharge l'audio et retourne le lien directement"""
    try:
        data = request.get_json(force=True)
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL manquante'}), 400
        
        download_id = str(uuid.uuid4())[:8]
        output_path = f'/tmp/audio_{download_id}'
        
        has_ffmpeg = os.path.exists('/usr/bin/ffmpeg') or os.system('which ffmpeg') == 0
        
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
            duration = info.get('duration', 0)
        
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
        
        file_size = os.path.getsize(audio_file)
        
        downloads[download_id] = {
            'path': audio_file,
            'title': title,
            'duration': duration,
            'size': file_size,
            'timestamp': time.time()
        }
        
        file_url = f'https://web-production-4bea.up.railway.app/file/{download_id}.mp3'
        
        return jsonify({
            'success': True,
            'message': 'Audio ready',
            'title': title,
            'file_url': file_url,
            'download_id': download_id,
            'duration': duration,
            'file_size': file_size
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Erreur: {str(e)}',
            'success': False
        }), 400

@app.route('/file/<path:filename>')
def get_file(filename):
    """Récupère le fichier audio"""
    download_id = filename.replace('.mp3', '').replace('.m4a', '').replace('.webm', '')
    
    if download_id not in downloads:
        return jsonify({'error': 'File not found'}), 404
    
    file_data = downloads[download_id]
    
    if not os.path.exists(file_data['path']):
        return jsonify({'error': 'File no longer available'}), 404
    
    return send_file(
        file_data['path'],
        mimetype='audio/mpeg',
        as_attachment=False
    )

@app.route('/file-base64/<download_id>', methods=['GET'])
def get_file_base64(download_id):
    """Retourne le fichier en base64 pour Bubble"""
    if download_id not in downloads:
        return jsonify({'error': 'File not found'}), 404
    
    file_data = downloads[download_id]
    
    if not os.path.exists(file_data['path']):
        return jsonify({'error': 'File no longer available'}), 404
    
    import base64
    with open(file_data['path'], 'rb') as f:
        file_content = f.read()
        base64_content = base64.b64encode(file_content).decode('utf-8')
    
    return jsonify({
        'success': True,
        'filename': f"{file_data['title']}.mp3",
        'base64': base64_content,
        'size': file_data['size']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
