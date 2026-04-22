# ANN-D Health Advisor - OTP Auth (Flask)

Modern OTP-based authentication (Email OTP + Mobile OTP) for the **ANN-D Health Advisor** UI.

## 1) Setup

```powershell
cd flask_auth
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:
- `http://127.0.0.1:5000/auth`

After login, you'll be redirected to:
- `http://127.0.0.1:5000/chatbot/` (serves `../ann-d-web/` behind session login)

## 2) Email OTP (Gmail SMTP)

Set environment variables (use a Gmail **App Password**):

```powershell
$env:FLASK_SECRET_KEY="change-me"
$env:GMAIL_USER="yourgmail@gmail.com"
$env:GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
$env:SMTP_FROM="ANN-D Health Advisor <yourgmail@gmail.com>"
```

If SMTP is not configured, the OTP is logged to the Flask server console (dev-only).

## 3) Mobile OTP (Mock or Twilio)

By default, SMS is mocked (OTP logged to server console).

Optional Twilio:

```powershell
pip install twilio
$env:TWILIO_ACCOUNT_SID="ACxxxxxxxx"
$env:TWILIO_AUTH_TOKEN="xxxxxxxx"
$env:TWILIO_FROM_NUMBER="+1XXXXXXXXXX"
```

## 4) Point to a different chatbot UI folder (optional)

```powershell
$env:CHATBOT_STATIC_DIR="ann-d-web"
```
