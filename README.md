# plaud-local

Alternative locale à Plaud — transcription et analyse de RDV clients.
100% local, RTX 3070, aucune donnée envoyée dans le cloud.

## Prérequis

- Python 3.11+
- [Ollama](https://ollama.com) installé et `mistral` téléchargé
- CUDA (drivers Nvidia à jour)
- Token HuggingFace gratuit (pour pyannote)

## Installation

```bash
# 1. Cloner / copier le projet
cd plaud-local

# 2. Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate   # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer
copy .env.example .env
# Editer .env : ajouter ton HF_TOKEN

# 5. Télécharger le modèle Ollama
ollama pull mistral

# 6. Lancer
python backend/main.py
```

L'app est accessible sur `http://localhost:8000`

## Accès depuis le téléphone (même WiFi)

```
http://<IP-de-ton-PC>:8000
```

Trouver ton IP : `ipconfig` → "Adresse IPv4"

## Accès depuis n'importe où (Tailscale)

1. Installer Tailscale sur le PC et le téléphone
2. Connexion avec le même compte
3. Utiliser l'IP Tailscale du PC (`100.x.x.x:8000`)

## Token HuggingFace

1. Créer un compte sur [huggingface.co](https://huggingface.co)
2. Settings → Access Tokens → New token (Read)
3. Accepter les conditions de pyannote :
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
4. Coller le token dans `.env`
