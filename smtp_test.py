
import os
import smtplib
from dotenv import load_dotenv

load_dotenv(override=True)

username = os.getenv("MAIL_USERNAME", "").strip()
password = os.getenv("MAIL_PASSWORD", "").strip().replace(" ", "")

try:
    print("Connecting to Gmail...")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        
        server.ehlo()
        server.starttls()
        server.ehlo()

        print("Testing Gmail authentication...")

        server.login(username, password)

        print("GMAIL LOGIN SUCCESSFUL!")

except Exception as error:
    print("LOGIN FAILED:", repr(error))
