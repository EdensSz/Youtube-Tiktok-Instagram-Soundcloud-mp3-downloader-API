import subprocess
import sys

def telecharger_audio(url):
    """
    Télécharge l'audio d'une vidéo YouTube, TikTok ou Instagram
    """
    try:
        # Commande yt-dlp pour extraire uniquement l'audio
        commande = [
            'yt-dlp',
            '-x',  # Extraire l'audio
            '--audio-format', 'mp3',  # Format MP3
            '--audio-quality', '0',  # Meilleure qualité
            '-o', '%(title)s.%(ext)s',  # Nom du fichier
            url
        ]
        
        print(f"Téléchargement en cours de : {url}")
        subprocess.run(commande, check=True)
        print("✓ Téléchargement terminé !")
        
    except subprocess.CalledProcessError:
        print("✗ Erreur lors du téléchargement")
    except FileNotFoundError:
        print("✗ yt-dlp n'est pas installé. Installez-le avec: pip install yt-dlp")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Entrez l'URL de la vidéo : ")
    
    telecharger_audio(url)
