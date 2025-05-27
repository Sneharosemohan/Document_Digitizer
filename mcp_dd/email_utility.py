#Importing libraries for email workflow
import email
from email.header import decode_header
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os 
import sys
import nest_asyncio
nest_asyncio.apply()

#Constants
# Get the directory of the current script
BASE_DIR = os.getcwd()
CONFIG_FILEPATH = os.path.join(BASE_DIR, "config.json")
EMAIL_FOLDER = os.path.join(BASE_DIR, "data/email_attachments")

def get_imap_server(username):
    imap_servers = {
        "gmail.com": "imap.gmail.com",
        "outlook.com": "outlook.office365.com",
        "hotmail.com": "outlook.office365.com",
        "yahoo.com": "imap.mail.yahoo.com",
        "icloud.com": "imap.mail.me.com",
        "aol.com": "imap.aol.com",
    }
    domain = username.split('@')[-1]
    return imap_servers.get(domain, "Unknown IMAP server")


def fetch_email_details(mail, email_id):
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            sender = msg["From"]
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            body = ""
            attachments = []
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            filepath = os.path.join(EMAIL_FOLDER, filename)
                            if not os.path.exists(filepath):
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                            attachments.append(filename)
                    elif content_type == "text/plain" and "attachment" not in content_disposition:
                        body = part.get_payload(decode=True).decode()
            else:
                body = msg.get_payload(decode=True).decode()
            return {"sender": sender, "subject": subject, "body": body, "attachments": attachments}
