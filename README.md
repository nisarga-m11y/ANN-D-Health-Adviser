# Personalized Health Advice and Symptom Checking Chatbot

Full-stack AI chatbot application using:
- Backend: Django + Django REST Framework
- Frontend: React.js + HTML + CSS (Vite)
- Database: MySQL
- ML: Scikit-learn
- NLP: NLTK

## 1. Project Folder Structure

```text
chatbot/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── __init__.py
│   │   ├── accounts/
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── apps.py
│   │   │   ├── managers.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── urls.py
│   │   │   ├── views.py
│   │   │   └── migrations/
│   │   │       └── __init__.py
│   │   └── chatbot/
│   │       ├── __init__.py
│   │       ├── admin.py
│   │       ├── apps.py
│   │       ├── models.py
│   │       ├── nlp_utils.py
│   │       ├── serializers.py
│   │       ├── services.py
│   │       ├── urls.py
│   │       ├── views.py
│   │       └── migrations/
│   │           └── __init__.py
│   └── ml/
│       ├── sample_symptoms.csv
│       └── train_model.py
├── frontend/
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── api/
│       │   ├── auth.js
│       │   ├── chat.js
│       │   └── client.js
│       ├── components/
│       │   ├── Navbar.jsx
│       │   └── ProtectedRoute.jsx
│       ├── context/
│       │   └── AuthContext.jsx
│       ├── pages/
│       │   ├── ChatbotDashboard.jsx
│       │   ├── HealthReportPage.jsx
│       │   ├── HomePage.jsx
│       │   ├── LoginPage.jsx
│       │   └── RegisterPage.jsx
│       └── styles/
│           └── global.css
└── README.md
```

## 2. Sample Dataset Format (Symptoms vs Disease)

CSV format (`backend/ml/sample_symptoms.csv`):

```csv
symptom,disease
"fever cough sore throat",Flu
"runny nose sneezing mild fever",Common Cold
"headache nausea light sensitivity",Migraine
```

## 3. Backend Setup (Django)

By default the backend uses SQLite (ackend/db.sqlite3) for easy local dev.

- To use MySQL instead, set USE_MYSQL=True in ackend/.env and make sure your MySQL server is running.

1. Create MySQL database:
   - `CREATE DATABASE health_chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`

2. Create and activate Python virtual environment:
   - Windows:
     - `cd backend`
     - `python -m venv venv`
     - `venv\Scripts\activate`

3. Install dependencies:
   - `pip install -r requirements.txt`

4. Configure environment:
   - Copy `backend/.env.example` to `backend/.env`
   - Update MySQL credentials and secret key

5. Run migrations:
   - `python manage.py makemigrations accounts chatbot`
   - `python manage.py migrate`

6. Train ML model and save pickle files:
   - `python ml/train_model.py`

7. Create admin user (optional):
   - `python manage.py createsuperuser`

8. Start backend:
   - `python manage.py runserver`

Backend base URL:
- `http://127.0.0.1:8000`

## 4. Frontend Setup (React)

1. Install Node.js 18+.
2. In new terminal:
   - `cd frontend`
   - `npm install`
3. Configure environment:
   - Copy `frontend/.env.example` to `frontend/.env`
4. Start frontend:
   - `npm run dev`

Frontend URL:
- `http://localhost:5173`

## 5. Django + React Integration

- React Axios client points to `VITE_API_BASE_URL` (default: `http://127.0.0.1:8000/api`)
- Django CORS allows `http://localhost:5173`
- Auth flow:
  - Register/Login returns DRF token
  - Token saved in browser local storage
  - Token automatically sent in `Authorization: Token <token>`

## 6. API Endpoints (Django REST Framework)

Auth:
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`

Chatbot:
- `POST /api/chat/predict/` (ML prediction only)
  - Input: `{ "message": "fever, cough, body ache" }`
  - Output: disease prediction, confidence, advice
- `POST /api/chat/message/` (prediction + save in history)
- `GET /api/chat/history/`
## 7. Database Design

1. `users` table (custom Django auth model)
- `id`, `name`, `email`, `password`, auth/status fields

2. `chat_history` table
- `id`, `user_id`, `message`, `response`, `predicted_disease`, `advice`, `timestamp`

3. `symptoms_data` table
- `id`, `symptom`, `disease`

## 8. Implemented Features

- User authentication (register/login/logout)
- Modern chatbot-like dashboard
- NLP preprocessing (tokenization + stopword removal)
- ML symptom classification (Naive Bayes with TF-IDF)
- Personalized health advice generation
- Chat history tracking and health report page
- Responsive design for mobile and desktop
- Error handling for invalid input and API failures

## 9. Important Disclaimer

This project provides educational AI-assisted symptom analysis and is not a medical diagnosis system. Users should consult qualified healthcare professionals for medical decisions.


## 10. System Architecture

1. React frontend captures user symptoms in natural language.
2. Request sent to Django REST API (/api/chat/predict/ or /api/chat/message/).
3. Django preprocesses text using NLTK (tokenization + stopword removal).
4. Scikit-learn model predicts likely disease from vectorized input.
5. Backend generates personalized health advice and safety disclaimer.
6. For chat mode, request + response are stored in MySQL chat_history.
7. React dashboard and health report display real-time and historical results.



## 11. Additional Requirements (Planned Features)

### Doctor Visit Companion
- Keep a "my symptoms timeline".
- Store medications list, allergies, and test reports.
- Generate a 1-page summary for the next appointment.

### Women Safety + Quick Help Mode
- Trigger phrase: "I feel unsafe".
- Show immediate steps and safety tips (no false promises).
- Provide location-sharing instructions.
- Trusted contacts checklist.
- Safe route tips.

### Senior Citizen Helper
- Medication reminders.
- Scam protection guidance.
- Simple explanations.
- "Call my family" prompts.
- Large-text voice UI.

### Image-to-Help
- Upload photos of prescriptions, bills, notices, or forms.
- Extract key information.
- Explain it in simple terms.

### Local Micro-Business Helper
- Stock list.
- Pricing tips.
- Simple invoice messages.
- Customer follow-up templates.

### Kitchen Planner
- Use budget + diet + local foods preferences.
- Generate weekly menu.
- Generate shopping list.
- Suggest "cook with what’s at home" options.

