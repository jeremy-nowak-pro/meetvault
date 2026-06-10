# plaud-local — Primer

## Objectif
Application web auto-hébergée de transcription et analyse de réunions clients, alternative gratuite à Plaud. 100% local, aucune donnée envoyée dans le cloud.

## Utilisateur
Jérémy — concepteur développeur freelance. Enregistre ses RDV clients (1h-1h30, 2 à 4 personnes) pour en extraire automatiquement les demandes client, décisions, engagements et points en suspens. Accès depuis son téléphone (navigateur mobile).

## Stack technique
- **Backend** : Python + FastAPI
- **Transcription** : faster-whisper large-v3 (GPU — RTX 3070 8Go)
- **Diarisation** : pyannote.audio 3.x (qui a dit quoi)
- **Analyse** : Ollama + Mistral 7B (extraction structurée métier freelance)
- **Base de données** : SQLite via SQLAlchemy (simple, pas de serveur)
- **Frontend** : HTML/CSS/JS vanilla + Tailwind CDN (mobile-first, PWA)
- **Export** : Markdown + PDF (via weasyprint)
- **Accès distant** : Tailscale (VPN peer-to-peer, 0 port ouvert)

## Matériel cible
- PC : AMD Ryzen 7 5800X, 64 Go RAM, RTX 3070 8Go VRAM
- OS : Windows 10 Pro
- Whisper large-v3 tient en VRAM (6Go), Ollama Mistral 7B tient aussi (4-5Go)
- Pipeline séquentiel : pas de conflit VRAM entre les deux

## Architecture des données
```
Client
└── Projet
    └── RDV (audio + transcription + analyse)
        ├── Demandes client (todo)
        ├── Validations client
        ├── Questions/Réponses
        ├── Engagements pris par Jérémy
        └── Points en suspens
```

## Output prioritaire (prompt Ollama calibré freelance dev)
1. Demandes client (liste de tâches)
2. Ce que le client a validé
3. Questions posées + réponses données (+ flag si non répondu)
4. Engagements de Jérémy
5. Points en suspens / à confirmer
6. Prochaine étape suggérée

## Décisions d'architecture
- **SQLite** plutôt que PostgreSQL : déploiement simplifié, un seul fichier, suffisant pour un usage solo
- **faster-whisper** plutôt que whisper original : 4x plus rapide, même précision, optimisé CTranslate2
- **Vanilla JS** plutôt que React/Next.js : pas de build step, chargement instantané, suffisant pour l'usage
- **Tailscale** plutôt que port forwarding : sécurité maximale, 0 configuration routeur
- **Pas de Docker** pour commencer : évite la complexité GPU passthrough sur Windows, lancement direct Python

## Ce qui est hors scope
- Application mobile native (pas d'App Store)
- Multi-utilisateurs / multi-comptes
- Synchronisation cloud
- Intégration CRM externe (Notion, HubSpot...)
- Traitement temps réel pendant l'enregistrement

## Structure du projet
```
plaud-local/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── database.py             # SQLite + SQLAlchemy
│   ├── models.py               # Client, Projet, RDV
│   ├── routers/
│   │   ├── clients.py
│   │   ├── projects.py
│   │   └── meetings.py
│   └── pipeline/
│       ├── transcriber.py      # faster-whisper
│       ├── diarizer.py         # pyannote
│       ├── analyzer.py         # Ollama Mistral
│       └── exporter.py         # PDF/Markdown
├── frontend/
│   ├── index.html              # Dashboard clients
│   ├── record.html             # Enregistrement mobile
│   └── meeting.html            # Résultat RDV
├── storage/
│   └── audio/                  # Fichiers audio locaux
├── requirements.txt
└── primer.md
```

## Lancement
```bash
cd plaud-local
pip install -r requirements.txt
python backend/main.py
# → http://localhost:8000
# → http://<tailscale-ip>:8000 depuis le téléphone
```

## Points d'attention
- pyannote nécessite un token HuggingFace (gratuit) pour télécharger le modèle
- Ollama doit être installé séparément (ollama.com) et avoir `mistral` pulled
- faster-whisper télécharge le modèle large-v3 au premier lancement (~3Go)
- Le pipeline est séquentiel : Whisper libère la VRAM avant qu'Ollama tourne
