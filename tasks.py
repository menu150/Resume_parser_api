from fastapi_utils.tasks import repeat_every
from fastapi import FastAPI
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText

DB_PATH = os.getenv("API_KEY_DB", "api_keys.db")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_SENDER = os.getenv("SMTP_SENDER", "no-reply@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "password")

app = FastAPI()

# Ensure alert_sent column exists on startup
@app.on_event("startup")
def init_alert_column():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            ALTER TABLE api_keys ADD COLUMN alert_sent BOOLEAN DEFAULT 0
        """)
        # Ignore if column already exists
        conn.commit()

@app.on_event("startup")
@repeat_every(seconds=600)  # every 10 minutes
def check_quota_alerts():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT key, quota, used, email FROM api_keys
            WHERE alert_sent = 0 AND used >= (quota * 0.9)
        """)
        alerts = cursor.fetchall()

        for key, quota, used, email in alerts:
            msg = MIMEText(f"You're using {used}/{quota} of your ResumeParse API quota. Consider upgrading your plan.")
            msg['Subject'] = "⚠️ Quota Warning: 90% Reached"
            msg['From'] = SMTP_SENDER
            msg['To'] = email

            try:
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(SMTP_SENDER, SMTP_PASSWORD)
                    server.sendmail(SMTP_SENDER, email, msg.as_string())
                print(f"📧 Quota alert sent to {email}")
            except Exception as e:
                print(f"❌ Failed to send quota alert: {e}")

            cursor.execute("UPDATE api_keys SET alert_sent = 1 WHERE key = ?", (key,))
        conn.commit()
