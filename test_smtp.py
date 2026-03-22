import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ← PASTE YOUR DETAILS HERE
EMAIL = "asishmishra005@gmail.com"
PASSWORD = "womm lfuj rjga foiu"  # ← your 16 char app password

try:
    print("Connecting to Gmail...")
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    print("Logging in...")
    server.login(EMAIL, PASSWORD)
    print("✅ LOGIN SUCCESS! Email will work!")
    
    # Send test email
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg["Subject"] = "ScholarAI Test Email"
    msg.attach(MIMEText("<h1>Email is working!</h1>", "html"))
    server.send_message(msg)
    print("✅ TEST EMAIL SENT! Check your Gmail inbox!")
    server.quit()

except smtplib.SMTPAuthenticationError:
    print("❌ WRONG PASSWORD — App password is incorrect!")
    print("Go to: https://myaccount.google.com/apppasswords")
    print("Create new app password and paste it here")

except smtplib.SMTPException as e:
    print(f"❌ SMTP ERROR: {e}")

except Exception as e:
    print(f"❌ ERROR: {e}")
