---
name: Projet plaud-local
description: Application de transcription/analyse de RDV clients pour Jérémy (freelance dev), alternative locale à Plaud
type: project
---

Application web auto-hébergée de transcription de réunions clients. 100% local, Python + FastAPI + Whisper + pyannote + Ollama.

**Why:** Jérémy est concepteur développeur freelance et veut capturer automatiquement les demandes clients, décisions et engagements lors de ses RDV (1h-1h30, 2-4 personnes) sans payer un abonnement cloud.

**How to apply:** Le projet est dans `c:/Users/33638/Documents/Dev/plaud-local/`. Lire le `primer.md` à la racine pour reprendre le contexte complet. Stack : faster-whisper large-v3 (GPU RTX 3070), pyannote.audio, Ollama Mistral 7B, SQLite, Vanilla JS mobile-first. Pas de Docker pour commencer (complexité GPU Windows). Tailscale pour accès mobile depuis l'extérieur.
