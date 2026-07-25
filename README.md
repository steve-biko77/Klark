# Klark

Klark est un monorepo qui centralise la veille de contenu, la génération de posts assistée par IA et
leur publication planifiée sur les réseaux sociaux.

## Structure du repo

```
klark/
├── frontend/        # Next.js 16 + TypeScript + Tailwind
├── backend/         # FastAPI + Supabase
├── workers/         # Celery (scraping, scoring, publication)
├── docs/            # Diagrammes + cahier des charges
├── docker-compose.yml
├── .gitignore
└── .env.example
```

## Prérequis

- Node.js 20+
- Python 3.11+
- Docker et Docker Compose (pour Redis / PostgreSQL / lancement conteneurisé)
- Un projet [Supabase](https://supabase.com) (URL + clés anon/service)

## Configuration

1. Copier le fichier d'exemple à la racine :

   ```bash
   cp .env.example backend/.env
   ```

2. Renseigner les valeurs Supabase dans `backend/.env` (`SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_KEY`).
3. Créer `frontend/.env.local` avec les variables `NEXT_PUBLIC_SUPABASE_URL` et
   `NEXT_PUBLIC_SUPABASE_ANON_KEY` (voir `.env.example`).

## Lancement en local (sans Docker)

### Backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn "supabase" pydantic-settings
uvicorn app.main:app --reload --port 8000
```

L'API est disponible sur `http://localhost:8000` (route de santé : `GET /health`).

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Le frontend est disponible sur `http://localhost:3000`.

### Workers (Celery)

```bash
cd workers
python3 -m venv venv
source venv/bin/activate
pip install -e .
celery -A celery_app worker --loglevel=info
```

## Lancement avec Docker Compose

```bash
docker compose up --build
```

Cela démarre l'API FastAPI, le worker Celery, Redis et PostgreSQL.

## Conventions

- **Branches** : `main` (production stable), `dev` (intégration des features), `feature/*`
  (travail en cours, mergées via PR dans `dev`).
- **Commits** : `feat:` / `fix:` / `chore:` / `docs:`.
- Aucun secret ne doit être commité : utiliser `.env.example` comme référence et garder les
  fichiers `.env` / `.env.local` locaux (déjà exclus par `.gitignore`).
