import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_evaluation_email(recipient_email: str, candidate_resume: str, evaluation_report: str) -> bool:
    """
    Sends the evaluation email using SMTP.
    Requires .env variables:
    EMAIL_HOST (e.g., "smtp.gmail.com")
    EMAIL_PORT (e.g., 587)
    EMAIL_USER (your-email@gmail.com)
    EMAIL_PASS (your-app-password)
    """
    
    # Get SMTP settings from environment variables
    email_host = os.getenv("EMAIL_HOST")
    email_port = int(os.getenv("EMAIL_PORT", 587))
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS") # Use an "App Password" for Gmail

    if not all([email_host, email_port, email_user, email_pass]):
        print("Email configuration is missing. Skipping email.")
        return False
        
    # Create the email message
    subject = "AI Interview Evaluation Report"
    sender_email = email_user
    
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email
    
    # Create the HTML body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            h2 {{ color: #333; }}
            h3 {{ color: #555; }}
            pre {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h2>AI Interview Evaluation Complete</h2>
        
        <h3>Evaluation Report</h3>
        <pre>{evaluation_report.replace('**', '<b>').replace('**', '</b>').replace('*', '<li>')}</pre>
        
        <h3>Candidate Resume (Raw Text)</h3>
        <pre>{candidate_resume}</pre>
        
        <p>This is an automated report from the AI Interview Agent.</p>
    </body>
    </html>
    """
    
    message.attach(MIMEText(html_body, "html"))
    
    # Send the email
    try:
        with smtplib.SMTP(email_host, email_port) as server:
            server.starttls()  # Secure the connection
            server.login(email_user, email_pass)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Email successfully sent to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
