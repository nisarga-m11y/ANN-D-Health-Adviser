# ANN-D Health Advisor

Full-stack health assistant application:
- Backend: Django + DRF
- Frontend: React (Vite)
- Database: SQLite by default (MySQL optional via env)

## Quick Start (Run Anywhere with Docker)

### Prerequisites
- Docker Desktop (or Docker Engine + Compose)

### 1. Clone and enter project
```bash
git clone <your-repo-url>
cd ANN-D-Health-Adviser
```

### 2. Create backend env
```bash
cp backend/.env.example backend/.env
```

On Windows PowerShell:
```powershell
Copy-Item backend\.env.example backend\.env
```

### 3. Start the full website
```bash
docker compose up --build
```

### 4. Open in browser
- Website: `http://localhost:8080`
- Backend API root: `http://localhost:8000/api/`

## Stop the App
```bash
docker compose down
```

## Notes
- Frontend and backend are containerized.
- Frontend Nginx proxies `/api` and `/media` to backend.
- Backend runs migrations automatically on startup.

## Local Development (Without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Windows PowerShell: Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env      # Windows PowerShell: Copy-Item .env.example .env
npm run dev
```

Frontend local URL: `http://localhost:5173`

## Deploy to Render (Public Website)

### A. Push code to GitHub
Render deploys from a Git repository, so first push this project to GitHub.

### B. Create Backend service on Render
1. In Render dashboard, click `New +` -> `Web Service`.
2. Connect your GitHub repo and choose this project.
3. Choose `Docker` and set:
   - Root Directory: `backend`
   - Dockerfile Path: `./backend/Dockerfile`
4. Add environment variables:
   - `DJANGO_SECRET_KEY` = long random string
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `*`
   - `USE_MYSQL` = `False`
   - `EMERGENCY_CALL_NUMBER` = `108`
   - Optional: `GEMINI_API_KEY`, `EMAIL_*`, `TWILIO_*`
5. Deploy and copy backend URL, for example:
   - `https://your-backend.onrender.com`

### C. Create Frontend static site on Render
1. In Render dashboard, click `New +` -> `Static Site`.
2. Select the same GitHub repo.
3. Set:
   - Root Directory: `frontend`
   - Build Command: `npm ci && npm run build`
   - Publish Directory: `dist`
4. Add environment variable:
   - `VITE_API_BASE_URL` = `https://your-backend.onrender.com/api`
5. Deploy.

After deploy, Render gives a public frontend URL. That is your live website.

## Disclaimer
This application is for educational support and not a replacement for professional medical diagnosis or treatment.
