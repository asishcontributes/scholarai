from flask_mail import Mail, Message

mail = Mail()

def init_mail(app):
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='your_email@gmail.com',
        MAIL_PASSWORD='your_app_password'
    )
    mail.init_app(app)

def send_deadline_alert(email, scholarship):
    msg = Message(
        subject="Scholarship Deadline Reminder",
        sender="your_email@gmail.com",
        recipients=[email]
    )
    msg.body = f"Apply for {scholarship['name']} before {scholarship['deadline']}.\n{scholarship['link']}"
    mail.send(msg)