# app/services/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        self.smtp_host = settings.MAIL_HOST
        self.smtp_port = settings.MAIL_PORT
        self.username = settings.MAIL_USERNAME
        self.password = settings.MAIL_PASSWORD
        self.from_address = settings.MAIL_FROM_ADDRESS
        self.from_name = settings.MAIL_FROM_NAME
        self.encryption = settings.MAIL_ENCRYPTION

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str = None
    ) -> bool:
        """Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_address}>"
            msg["To"] = to_email

            # Attach text/plain part
            if text_body:
                msg.attach(MIMEText(text_body, "plain"))
            
            # Attach text/html part
            msg.attach(MIMEText(html_body, "html"))

            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.encryption == "tls":
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_password_reset_email(self, to_email: str, reset_token: str, user_name: str = None) -> bool:
        """Send password reset email with token.
        
        Args:
            to_email: User's email address
            reset_token: Password reset JWT token
            user_name: User's full name (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Create reset link
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        # Prepare email content
        subject = "Password Reset Request - Sinhala Educational Assistant"
        
        greeting = f"Hello {user_name}," if user_name else "Hello,"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background-color: #4CAF50; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px; 
                    margin: 20px 0;
                }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>{greeting}</p>
                <p>We received a request to reset your password for your Sinhala Educational Assistant account.</p>
                <p>Click the button below to reset your password:</p>
                <a href="{reset_link}" class="button">Reset Password</a>
                <p>Or copy and paste this link into your browser:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p><strong>This link will expire in 15 minutes.</strong></p>
                <p>If you didn't request a password reset, you can safely ignore this email.</p>
                <div class="footer">
                    <p>Best regards,<br>Sinhala Educational Assistant Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Password Reset Request
        
        {greeting}
        
        We received a request to reset your password for your Sinhala Educational Assistant account.
        
        Click the link below to reset your password:
        {reset_link}
        
        This link will expire in 15 minutes.
        
        If you didn't request a password reset, you can safely ignore this email.
        
        Best regards,
        Sinhala Educational Assistant Team
        """
        
        return self.send_email(to_email, subject, html_body, text_body)
