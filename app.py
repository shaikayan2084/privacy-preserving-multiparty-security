"""
SMPC Privacy-Preserving Data Collaboration - Flask Application
Security Features: Rate limiting, RBAC, MFA, Session management,
                   Email verification, Secure cookies, Logging
"""

import os
import logging
import secrets
import hashlib
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    jsonify,
    abort,
    make_response,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import bcrypt
import pyotp
import qrcode
import io
import base64

load_dotenv()

# ─── APP INIT ────────────────────────────────────────────────────────────────
app = Flask(__name__)

_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
    )
app.config["SECRET_KEY"] = _secret_key
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///smpc_app.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session Security
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("FLASK_ENV", "production") == "production"
)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)
app.config["WTF_CSRF_TIME_LIMIT"] = 3600


# ─── SECURITY HEADERS ─────────────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


# Mail config
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
    "MAIL_DEFAULT_SENDER", "noreply@smpc.local"
)

# ─── EXTENSIONS ──────────────────────────────────────────────────────────────
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"
login_manager.session_protection = "strong"
csrf = CSRFProtect(app)
mail = Mail(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ─── LOGGING ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
)
security_logger = logging.getLogger("security")
app_logger = logging.getLogger("app")


# ─── MODELS ──────────────────────────────────────────────────────────────────
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    users = db.relationship("User", backref="role", lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), default=2)

    # Email verification
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    verification_token_expiry = db.Column(db.DateTime)

    # Password reset
    reset_token = db.Column(db.String(100))
    reset_token_expiry = db.Column(db.DateTime)
    reset_token_used = db.Column(db.Boolean, default=False)

    # MFA
    mfa_secret = db.Column(db.String(32))
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_verified_at = db.Column(db.DateTime)

    # Security
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Session token rotation
    session_token = db.Column(db.String(100))

    def set_password(self, password):
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode(), salt).decode()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def generate_verification_token(self):
        token = secrets.token_urlsafe(32)
        self.verification_token = hashlib.sha256(token.encode()).hexdigest()
        self.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
        return token

    def generate_reset_token(self):
        token = secrets.token_urlsafe(32)
        self.reset_token = hashlib.sha256(token.encode()).hexdigest()
        self.reset_token_expiry = datetime.utcnow() + timedelta(minutes=30)
        self.reset_token_used = False
        return token

    def generate_session_token(self):
        self.session_token = secrets.token_hex(32)
        return self.session_token

    def get_mfa_uri(self):
        issuer = os.getenv("OTP_ISSUER", "SMPCShield")
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.email, issuer_name=issuer
        )


class LoginLog(db.Model):
    __tablename__ = "login_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    email_attempted = db.Column(db.String(120))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(300))
    success = db.Column(db.Boolean)
    failure_reason = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(200))
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# ─── HELPERS ─────────────────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def log_activity(user_id, action):
    log = ActivityLog(user_id=user_id, action=action, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()


def log_login(email, success, user_id=None, reason=None):
    log = LoginLog(
        user_id=user_id,
        email_attempted=email,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:300],
        success=success,
        failure_reason=reason,
    )
    db.session.add(log)
    db.session.commit()
    if not success:
        security_logger.warning(
            f"FAILED LOGIN: {email} from {request.remote_addr} — {reason}"
        )


def require_role(role_name):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not current_user.role or current_user.role.name != role_name:
                abort(403)
            return f(*args, **kwargs)

        return decorated

    return decorator


def require_mfa_verified(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.mfa_enabled and not session.get("mfa_verified"):
            return redirect(url_for("auth.mfa_verify"))
        return f(*args, **kwargs)

    return decorated


def send_verification_email(user, token):
    try:
        verify_url = url_for("auth.verify_email", token=token, _external=True)
        msg = Message(
            subject="Verify your SMPC account",
            recipients=[user.email],
            html=render_template(
                "auth/email_verify.html", user=user, verify_url=verify_url
            ),
        )
        mail.send(msg)
    except Exception as e:
        app_logger.error(f"Email send failed: {e}")


def send_reset_email(user, token):
    try:
        reset_url = url_for("auth.reset_password_confirm", token=token, _external=True)
        msg = Message(
            subject="Reset your SMPC password",
            recipients=[user.email],
            html=render_template(
                "auth/email_reset.html", user=user, reset_url=reset_url
            ),
        )
        mail.send(msg)
    except Exception as e:
        app_logger.error(f"Reset email failed: {e}")


# ─── BLUEPRINTS ───────────────────────────────────────────────────────────────
from flask import Blueprint

# ── AUTH BLUEPRINT ────────────────────────────────────────────────────────────
auth = Blueprint("auth", __name__, url_prefix="/auth")


@auth.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Server-side validation
        if not all([username, email, password, confirm]):
            error = "All fields are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif not re.search(r"[A-Z]", password):
            error = "Password must contain at least one uppercase letter."
        elif not re.search(r"[a-z]", password):
            error = "Password must contain at least one lowercase letter."
        elif not re.search(r"\d", password):
            error = "Password must contain at least one digit."
        elif not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            error = "Password must contain at least one special character."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif not re.match(r"^[a-zA-Z0-9_]+$", username):
            error = "Username can only contain letters, numbers, and underscores."
        elif User.query.filter_by(email=email).first():
            error = "Account could not be created. Please check your details."
        elif User.query.filter_by(username=username).first():
            error = "Username not available. Please choose another."
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            token = user.generate_verification_token()
            db.session.add(user)
            db.session.commit()
            # Assign default role
            default_role = Role.query.filter_by(name="user").first()
            if default_role:
                user.role_id = default_role.id
                db.session.commit()
            send_verification_email(user, token)
            log_activity(user.id, "signup")
            flash("Account created! Please check your email to verify.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/signup.html", error=error)


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute;100 per hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        # Always take same time to prevent timing attacks
        dummy_hash = "$2b$12$" + "x" * 53
        bcrypt.checkpw(
            b"dummy",
            dummy_hash.encode() if user is None else user.password_hash.encode(),
        )

        GENERIC_ERROR = "Invalid credentials. Please try again."

        if not user or not user.is_active:
            log_login(email, False, reason="user_not_found")
            error = GENERIC_ERROR
        elif user.is_locked():
            mins = int((user.locked_until - datetime.utcnow()).seconds / 60) + 1
            error = f"Account temporarily locked. Try again in {mins} minute(s)."
            log_login(email, False, user.id, "account_locked")
        elif not user.check_password(password):
            user.login_attempts += 1
            if user.login_attempts >= int(os.getenv("MAX_LOGIN_ATTEMPTS", 5)):
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=int(os.getenv("ACCOUNT_LOCK_MINUTES", 15))
                )
                security_logger.warning(f"Account LOCKED: {email}")
            db.session.commit()
            log_login(email, False, user.id, "wrong_password")
            error = GENERIC_ERROR
        elif not user.is_verified:
            error = "Please verify your email before logging in."
            log_login(email, False, user.id, "not_verified")
        else:
            # Successful login
            user.login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            user.last_login_ip = request.remote_addr
            new_token = user.generate_session_token()  # Rotate session token
            db.session.commit()
            login_user(user, remember=False)
            session.permanent = True
            session["session_token"] = new_token
            session["mfa_verified"] = False
            log_login(email, True, user.id)
            log_activity(user.id, "login")
            if user.mfa_enabled:
                return redirect(url_for("auth.mfa_verify"))
            return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", error=error)


@auth.route("/logout")
@login_required
def logout():
    log_activity(current_user.id, "logout")
    session.clear()
    logout_user()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login"))


@auth.route("/verify-email/<token>")
def verify_email(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = User.query.filter_by(verification_token=token_hash).first()
    if (
        not user
        or not user.verification_token_expiry
        or user.verification_token_expiry < datetime.utcnow()
    ):
        flash("Verification link is invalid or expired.", "danger")
        return redirect(url_for("auth.login"))
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    db.session.commit()
    flash("Email verified! You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def forgot_password():
    message = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        # Generic message — never reveal if email exists
        message = "If that email is registered, a reset link has been sent."
        if user and user.is_verified:
            token = user.generate_reset_token()
            db.session.commit()
            send_reset_email(user, token)
            security_logger.info(f"Password reset requested for {email}")
    return render_template("auth/forgot_password.html", message=message)


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def reset_password_confirm(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = User.query.filter_by(reset_token=token_hash).first()
    error = None
    if (
        not user
        or user.reset_token_used
        or not user.reset_token_expiry
        or user.reset_token_expiry < datetime.utcnow()
    ):
        flash("Password reset link is invalid or expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            user.set_password(password)
            user.reset_token_used = True
            user.reset_token = None
            user.session_token = None  # Invalidate all sessions
            db.session.commit()
            security_logger.info(f"Password reset completed for {user.email}")
            flash("Password reset successfully. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token, error=error)


@auth.route("/mfa/setup", methods=["GET", "POST"])
@login_required
def mfa_setup():
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        totp = pyotp.TOTP(current_user.mfa_secret)
        if totp.verify(otp, valid_window=1):
            current_user.mfa_enabled = True
            current_user.mfa_verified_at = datetime.utcnow()
            db.session.commit()
            session["mfa_verified"] = True
            log_activity(current_user.id, "mfa_enabled")
            flash("MFA enabled successfully!", "success")
            return redirect(url_for("main.dashboard"))
        flash("Invalid OTP. Please try again.", "danger")

    if not current_user.mfa_secret:
        current_user.mfa_secret = pyotp.random_base32()
        db.session.commit()

    uri = current_user.get_mfa_uri()
    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template(
        "auth/mfa_setup.html", qr_b64=qr_b64, secret=current_user.mfa_secret
    )


@auth.route("/mfa/verify", methods=["GET", "POST"])
@login_required
def mfa_verify():
    if not current_user.mfa_enabled:
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        totp = pyotp.TOTP(current_user.mfa_secret)
        if totp.verify(otp, valid_window=1):
            session["mfa_verified"] = True
            log_activity(current_user.id, "mfa_verified")
            return redirect(url_for("main.dashboard"))
        error = "Invalid OTP. Please try again."
        security_logger.warning(f"Failed MFA attempt: user {current_user.id}")
    return render_template("auth/mfa_verify.html", error=error)


# ── MAIN BLUEPRINT ────────────────────────────────────────────────────────────
main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("pages/index.html")


@main.route("/about")
def about():
    return render_template("pages/about.html")


@main.route("/literature")
def literature():
    return render_template("pages/literature.html")


@main.route("/architecture")
def architecture():
    return render_template("pages/architecture.html")


@main.route("/results")
def results():
    return render_template("pages/results.html")


@main.route("/team")
def team():
    return render_template("pages/team.html")


@main.route("/dashboard")
@login_required
@require_mfa_verified
def dashboard():
    logs = (
        LoginLog.query.filter_by(user_id=current_user.id)
        .order_by(LoginLog.timestamp.desc())
        .limit(10)
        .all()
    )
    activity = (
        ActivityLog.query.filter_by(user_id=current_user.id)
        .order_by(ActivityLog.timestamp.desc())
        .limit(10)
        .all()
    )
    return render_template("dashboard/dashboard.html", logs=logs, activity=activity)


@main.route("/profile", methods=["GET", "POST"])
@login_required
@require_mfa_verified
def profile():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            old_pw = request.form.get("old_password", "")
            new_pw = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not current_user.check_password(old_pw):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters.", "danger")
            elif new_pw != confirm:
                flash("Passwords do not match.", "danger")
            else:
                current_user.set_password(new_pw)
                current_user.session_token = None
                db.session.commit()
                log_activity(current_user.id, "password_changed")
                flash("Password changed successfully.", "success")
    return render_template("dashboard/profile.html")


# ── ADMIN BLUEPRINT ───────────────────────────────────────────────────────────
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users")
@require_role("admin")
def user_list():
    users = User.query.all()
    return render_template("dashboard/admin_users.html", users=users)


@admin_bp.route("/logs")
@require_role("admin")
def security_logs():
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).limit(100).all()
    return render_template("dashboard/admin_logs.html", logs=logs)


@admin_bp.route("/toggle-user/<int:user_id>", methods=["POST"])
@require_role("admin")
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if user:
        user.is_active = not user.is_active
        db.session.commit()
        log_activity(current_user.id, f"toggled_user_{user_id}")
    return redirect(url_for("admin.user_list"))


# ── API BLUEPRINT ─────────────────────────────────────────────────────────────
api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/smpc/simulate", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def simulate_smpc():
    """Simulate SMPC computation — server-side validated"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    try:
        parties = int(data.get("parties", 3))
        threshold = int(data.get("threshold", 2))
        secret_val = int(data.get("secret", 42))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid parameter types"}), 400

    if not (2 <= parties <= 10) or not (2 <= threshold <= parties):
        return jsonify({"error": "Invalid parameters"}), 422

    prime = 2**31 - 1

    def poly_eval(coeffs, x, p):
        return sum(c * pow(x, i, p) for i, c in enumerate(coeffs)) % p

    coeffs = [secret_val % prime] + [
        secrets.randbelow(prime - 1) + 1 for _ in range(threshold - 1)
    ]
    shares = [(i, poly_eval(coeffs, i, prime)) for i in range(1, parties + 1)]

    log_activity(current_user.id, "smpc_simulation")
    return jsonify(
        {
            "parties": parties,
            "threshold": threshold,
            "shares": [
                {"x": x, "y_masked": f"{str(y)[:6]}...{str(y)[-4:]}"} for x, y in shares
            ],
            "reconstruction_possible": True,
            "security_note": f"Any {threshold} of {parties} shares reconstruct the secret. {threshold - 1} shares reveal nothing.",
            "protocol": "Shamir Secret Sharing over GF(p)",
            "prime": prime,
        }
    )


@api.route("/stats")
@login_required
@limiter.limit("60 per minute")
def stats():
    total_users = User.query.count()
    failed_logins = LoginLog.query.filter_by(success=False).count()
    successful_logins = LoginLog.query.filter_by(success=True).count()
    locked_users = User.query.filter(User.locked_until > datetime.utcnow()).count()
    return jsonify(
        {
            "total_users": total_users,
            "failed_logins": failed_logins,
            "successful_logins": successful_logins,
            "locked_accounts": locked_users,
            "mfa_enabled": User.query.filter_by(mfa_enabled=True).count(),
        }
    )


# ─── ERROR HANDLERS ───────────────────────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(429)
def too_many_requests(e):
    return render_template("errors/429.html"), 429


@app.errorhandler(500)
def server_error(e):
    app_logger.error(f"500 error: {e}")
    return render_template("errors/500.html"), 500


# ─── REGISTER BLUEPRINTS ──────────────────────────────────────────────────────
app.register_blueprint(auth)
app.register_blueprint(main)
app.register_blueprint(admin_bp)
app.register_blueprint(api)


# ─── DB INIT ─────────────────────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        if not Role.query.filter_by(name="admin").first():
            db.session.add(Role(name="admin", description="Full system access"))
            db.session.add(Role(name="user", description="Standard access"))
            db.session.commit()
        admin_email = os.getenv("ADMIN_EMAIL", "admin@smpc.local")
        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_password and not User.query.filter_by(email=admin_email).first():
            admin = User(username="admin", email=admin_email)
            admin.set_password(admin_password)
            admin.is_verified = True
            admin.role_id = Role.query.filter_by(name="admin").first().id
            admin.generate_session_token()
            db.session.add(admin)
            db.session.commit()
            app_logger.info(f"Admin user created with email: {admin_email}")
        elif not User.query.filter_by(email=admin_email).first():
            app_logger.warning(
                "No ADMIN_PASSWORD set in environment. "
                'Run: python -c "import secrets; print(secrets.token_urlsafe(16))" '
                "and set it as ADMIN_PASSWORD env var, then restart."
            )


if __name__ == "__main__":
    import os

    os.makedirs("logs", exist_ok=True)
    init_db()
    _debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=_debug, host="127.0.0.1", port=5000)
