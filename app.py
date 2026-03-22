from flask import Flask, render_template
from flask_cors import CORS
from flask_mail import Mail
from routes import routes

app = Flask(__name__)
app.secret_key = "super_secret_key_123"

# ==============================
# EMAIL CONFIGURATION
# ==============================
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "asishmishra005@gmail.com"   # ← your gmail
app.config["MAIL_PASSWORD"] = "womm lfuj rjga foiu"        # ← paste 16-char app password here
app.config["MAIL_DEFAULT_SENDER"] = ("ScholarAI", "asishmishra005@gmail.com")
app.config["MAIL_MAX_EMAILS"] = None
app.config["MAIL_ASCII_ATTACHMENTS"] = False

mail = Mail(app)

CORS(app)

app.register_blueprint(routes)

# Make mail available inside routes.py
app.extensions["mail"] = mail

if __name__ == "__main__":
    app.run(debug=True)