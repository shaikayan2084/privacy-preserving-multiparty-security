# 🔐 Privacy-Preserving Data Collaboration via SMPC

**B.Tech Final Year Project | Dept. CIC | Vasireddy Venkatadri Institute of Technology, Nambur**  
A.Y. 2025–2026 | Guide: Y. Suresh, Associate Professor

---

## 🚀 Quick Start (Local Development)

### 1. Clone the repository
```bash
git clone https://github.com/shaikayan2084/privacy-preserving-multiparty-security.git
cd privacy-preserving-multiparty-security
```

### 2. Create & activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment (SECURITY CRITICAL)
```bash
# Copy the sample .env
cp .env.example .env
```

**You MUST set these required values in `.env`:**
```bash
# Generate SECRET_KEY with:
python -c "import secrets; print(secrets.token_hex(32))"

# Generate ADMIN_PASSWORD with:
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

Edit `.env`:
- `SECRET_KEY` = (required) - the generated secret key
- `ADMIN_EMAIL` = admin email (optional, defaults to admin@smpc.local)
- `ADMIN_PASSWORD` = (required) - the generated admin password
- `MAIL_*` = your email credentials (Gmail with App Password recommended)

### 5. Run the application
```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## 🔑 Initial Admin Account
The admin account is created from environment variables on first run:
- Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`
- **Do NOT use default passwords in production!**

---

## 📂 Project Structure
```
privacy-preserving-multiparty-security/
├── app.py                  # Main Flask app — all routes & security logic
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (NOT in git)
├── .gitignore
├── logs/                   # Security & app logs (auto-created)
├── templates/
│   ├── base.html           # Shared layout
│   ├── auth/               # Login, signup, MFA, password reset
│   ├── dashboard/          # User dashboard, profile, admin panel
│   ├── pages/              # Public pages (home, about, etc.)
│   └── errors/             # 403, 404, 429, 500 error pages
└── static/                 # CSS, JS, images
```

---

## 🛡️ Security Features Implemented

| Feature | Implementation |
|---------|----------------|
| Rate Limiting | Flask-Limiter: 20/min login, 5/hr reset, 30/min API |
| Brute Force Protection | Lock after 5 fails for 15 minutes |
| Password Hashing | bcrypt with 12 rounds + salt |
| Strong Password Policy | Min 8 chars, uppercase, lowercase, digit, special char |
| Email Verification | SHA-256 token, 24hr expiry |
| Password Reset | Single-use token, 30min expiry |
| MFA / 2FA | TOTP via Google Authenticator / Authy |
| CSRF Protection | Flask-WTF CSRF tokens on all forms |
| Security Headers | CSP, X-Frame-Options, X-Content-Type-Options, HSTS |
| Session Security | HttpOnly cookies, session rotation on login |
| Session Expiry | 1-hour automatic expiry |
| Generic Error Messages | Never reveals if email exists |
| RBAC | Admin / User roles enforced server-side |
| SQL Injection Prevention | SQLAlchemy ORM parameterized queries |
| Security Logging | All login attempts logged with IP |
| Account Lockout | Temporary lock with configurable duration |
| Secret Key Validation | App fails fast if SECRET_KEY not set |

---

## 🔌 API Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/smpc/simulate` | Required | Run SMPC simulation |
| GET | `/api/stats` | Required | System statistics |

---

## 👥 Team Members
- P. Radha Krishna Sai (22BQ1A4774)
- Shaik Ayan (23BQ5A4709)
- V. Jaswanth Kumar (23BQ5A4710)
- D. Sai Aditya (23BQ5A4713)

---

## 📖 Opening in VS Code
```bash
code .
```
Or open the folder `D:\privacy-preserving-multiparty-security` in VS Code.

To run from VS Code terminal:
```bash
# Activate venv first
venv\Scripts\activate   # Windows
python app.py
```

---

## ⚠️ Production Notes
- Set `FLASK_ENV=production` in production for secure cookie settings
- Set `FLASK_DEBUG=false` in production (debug mode exposes sensitive info)
- Use PostgreSQL/MySQL instead of SQLite for production
- Configure a real SMTP server for emails
- Rotate `SECRET_KEY` periodically in production
- Never commit `.env` to git
- Use HTTPS in production (enables secure cookies)
- Review and update security headers as needed
