import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import os
from flask import current_app

class EmailSender:
    """Email sending utility class"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
    
    def send_email(self, to_email, subject, html_body, text_body=None):
        """
        Send email using SMTP configuration.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Get SMTP configuration
            smtp_server = current_app.config.get('SMTP_SERVER')
            smtp_port = current_app.config.get('SMTP_PORT', 587)
            smtp_username = current_app.config.get('SMTP_USERNAME')
            smtp_password = current_app.config.get('SMTP_PASSWORD')
            smtp_from_email = current_app.config.get('SMTP_FROM_EMAIL')
            smtp_from_name = current_app.config.get('SMTP_FROM_NAME')
            smtp_use_tls = current_app.config.get('SMTP_USE_TLS', True)
            
            if not all([smtp_server, smtp_username, smtp_password, smtp_from_email]):
                raise Exception("SMTP configuration incomplete")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((smtp_from_name, smtp_from_email))
            msg['To'] = to_email
            
            # Add text body if provided
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)
            
            # Add HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if smtp_use_tls:
                    server.starttls()
                
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_password_reset(self, user, reset_token):
        """
        Send password reset email.
        
        Args:
            user: User object
            reset_token: Password reset token
        
        Returns:
            True if sent successfully, False otherwise
        """
        app_name = current_app.config.get('APP_NAME', 'Scorpio Image Resizer')
        reset_link = f"{current_app.config.get('SERVER_NAME', 'http://localhost:5000')}/reset-password/{reset_token}"
        
        subject = f"Reset Your Password - {app_name}"
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reset Your Password</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    padding: 15px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔐 Password Reset</h1>
                <p>{app_name}</p>
            </div>
            <div class="content">
                <h2>Hello {user.username},</h2>
                <p>You requested a password reset for your {app_name} account.</p>
                <p>Click the button below to reset your password:</p>
                <div style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </div>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px;">
                    {reset_link}
                </p>
                <p><strong>This link expires in 24 hours.</strong></p>
                <p>If you didn't request this password reset, you can safely ignore this email.</p>
            </div>
            <div class="footer">
                <p>© 2025 {app_name}. All rights reserved.</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Reset Your Password - {app_name}
        
        Hello {user.username},
        
        You requested a password reset for your {app_name} account.
        
        Click here to reset your password:
        {reset_link}
        
        This link expires in 24 hours.
        
        If you didn't request this password reset, you can safely ignore this email.
        
        Best regards,
        {app_name} Team
        """
        
        return self.send_email(user.email, subject, html_body, text_body)
    
    def send_welcome_email(self, user):
        """
        Send welcome email to new user.
        
        Args:
            user: User object
        
        Returns:
            True if sent successfully, False otherwise
        """
        app_name = current_app.config.get('APP_NAME', 'Scorpio Image Resizer')
        login_url = current_app.config.get('SERVER_NAME', 'http://localhost:5000')
        
        subject = f"Welcome to {app_name}!"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Welcome to {app_name}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    padding: 15px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .feature {{
                    background: white;
                    padding: 20px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #667eea;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Welcome!</h1>
                <p>{app_name}</p>
            </div>
            <div class="content">
                <h2>Welcome to {app_name}, {user.username}!</h2>
                <p>Your account has been successfully created. You're now ready to process professional images with our powerful tools.</p>
                
                <div style="text-align: center;">
                    <a href="{login_url}" class="button">Login to Your Account</a>
                </div>
                
                <h3>What can you do with {app_name}?</h3>
                
                <div class="feature">
                    <h4>🖼️ Blur Tool</h4>
                    <p>Add professional blurred borders to your images with customizable intensity and dimensions.</p>
                </div>
                
                <div class="feature">
                    <h4>📦 Compress Tool</h4>
                    <p>Reduce image file sizes while maintaining quality, with target size or quality controls.</p>
                </div>
                
                <div class="feature">
                    <h4>📏 Resize Tool</h4>
                    <p>Resize images using percentage, maximum dimensions, or specific size methods.</p>
                </div>
                
                <div class="feature">
                    <h4>📦 Pack Processing</h4>
                    <p>Generate multiple outputs from a single image using pre-configured packs like the Scorpio Tix & Link Tree Pack.</p>
                </div>
                
                <p>If you have any questions, don't hesitate to contact our support team.</p>
            </div>
            <div class="footer">
                <p>© 2025 {app_name}. All rights reserved.</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to {app_name}!
        
        Hello {user.username},
        
        Your account has been successfully created. You're now ready to process professional images with our powerful tools.
        
        Login here: {login_url}
        
        What can you do with {app_name}?
        
        • Blur Tool: Add professional blurred borders to your images
        • Compress Tool: Reduce image file sizes while maintaining quality
        • Resize Tool: Resize images using multiple methods
        • Pack Processing: Generate multiple outputs from a single image
        
        If you have any questions, don't hesitate to contact our support team.
        
        Best regards,
        {app_name} Team
        """
        
        return self.send_email(user.email, subject, html_body, text_body)
    
    def test_email_configuration(self, test_email):
        """
        Test email configuration by sending a test email.
        
        Args:
            test_email: Email address to send test to
        
        Returns:
            True if sent successfully, False otherwise
        """
        app_name = current_app.config.get('APP_NAME', 'Scorpio Image Resizer')
        
        subject = f"Email Configuration Test - {app_name}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Email Test</title>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>✅ Email Configuration Test Successful!</h2>
            <p>This is a test email from {app_name}.</p>
            <p>Your SMTP configuration is working correctly.</p>
            <hr>
            <p><small>Sent at: {current_app.config.get('SMTP_SERVER')} on {os.name}</small></p>
        </body>
        </html>
        """
        
        text_body = f"""
        Email Configuration Test - {app_name}
        
        This is a test email from {app_name}.
        Your SMTP configuration is working correctly.
        """
        
        return self.send_email(test_email, subject, html_body, text_body)

# Create global email sender instance
email_sender = EmailSender()
