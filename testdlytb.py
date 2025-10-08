"""
api.py - API Flask ultra-simple pour télécharger l'audio
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)  # Permet les requêtes depuis n'importe quel domaine

# Stockage de la progression
progress_data = {}

def progress_hook(d, task_id):
    """Capture la progression"""
    if d['status'] == 'downloading':
        if 'total_bytes' in d:
            percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
            progress_data[task_id] = {'progress': round(percent, 1), 'status': 'downloading'}
    elif d['status'] == 'finished':
        progress_data[task_id] = {'progress': 100, 'status': 'finished'}

@app.route('/')
def home():
    return jsonify({'message': 'API de téléchargement audio active'})

@app.route('/download', methods=['POST'])
def download():
    """Endpoint principal pour télécharger l'audio"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL manquante'}), 400
        
        # Vérifier si l'URL est valide
        task_id = str(hash(url))
        progress_data[task_id] = {'progress': 0, 'status': 'starting'}
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'/tmp/audio_{task_id}.%(ext)s',
            'progress_hooks': [lambda d: progress_hook(d, task_id)],
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'audio')
            
        return jsonify({
            'success': True,
            'message': 'Téléchargement terminé',
            'title': title,
            'task_id': task_id
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': f'Erreur: {str(e)}',
            'success': False
        }), 400

@app.route('/progress/<task_id>')
def get_progress(task_id):
    """Obtenir la progression d'un téléchargement"""
    if task_id in progress_data:
        return jsonify(progress_data[task_id])
    return jsonify({'progress': 0, 'status': 'not_found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)