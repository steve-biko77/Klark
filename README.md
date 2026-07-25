# Klark

Klark est une plateforme d'automatisation de contenu éditorial : veille RSS, génération de posts LinkedIn assistée par IA (Claude), calendrier de publication et analytics d'engagement.

Suivi du produit : [Jira SCRUM](https://wkstevebiko1.atlassian.net/jira/software/projects/SCRUM/boards) — 5 epics (Infrastructure & Auth, Veille & Sources, Génération & Édition, Publication & Calendrier, Analytics & Rétention).

## Structure du repo

```
.
├── frontend/   # Next.js 16 (React 19, TypeScript, Tailwind) — dashboard, éditeur, calendrier
├── backend/    # Django 5 + DRF — API REST, auth JWT, modèles, intégrations (LinkedIn OAuth, Claude)
├── workers/    # Celery — tâches asynchrones (scraping RSS, scoring, publication programmée)
├── docs/       # Plans de développement et notes techniques
└── assets/     # Ressources visuelles (specs produit)
```

Le backend est organisé en apps Django par domaine métier : `authentication`, `sources`, `articles`, `posts`, `social`, `dashboard`, `analytics`, `billing`.

## Prérequis

- Node.js 20+
- Python 3.13+
- Docker & Docker Compose (recommandé pour Postgres/Redis en local)

## Démarrage rapide

```bash
# 1. Variables d'environnement
cp .env.example .env
cp backend/.env.example backend/.env
# éditer les valeurs (clés API, secrets) dans ces deux fichiers

# 2. Services d'infra (Postgres + Redis)
docker compose up postgres redis -d

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# 4. Frontend (dans un autre terminal)
cd frontend
npm install
npm run dev
```

Ou, à la racine, une fois les `.env` renseignés :

```bash
npm run dev:frontend   # équivalent à npm --prefix frontend run dev
```

Le frontend tourne sur `http://localhost:3000`, l'API Django sur `http://localhost:8000`.

## Tooling

- `run-klark.sh` : boucle d'agents Claude Code qui traite automatiquement les tickets Jira "À faire" du projet, un par un, dans une worktree Git dédiée (voir le script pour la configuration).
