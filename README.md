# Content-Creation

## Frontend (React via Vite)

Run locally:
- npm install
- npm run dev

API base options:
- Default backend: http://localhost:8000 (proxied for /api)
- Or set: VITE_API_BASE=http://127.0.0.1:8000 npm run dev

Open:
- http://localhost:5173 (AIAgent is rendered directly)

## Backend (Django)
- cd server
- python3 -m venv venv && source venv/bin/activate
- pip install Django django-cors-headers feedparser beautifulsoup4 requests python-dotenv
- python manage.py migrate
- python manage.py runserver 0.0.0.0:8000

## Endpoints
- /api/ai/generate/?type=news|events|success
- /api/social/linkedin/
- /api/social/instagram/