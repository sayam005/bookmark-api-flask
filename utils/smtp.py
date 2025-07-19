from flask_mail import Message
from config import mail
# --- UPDATE IMPORTS ---
from flask import current_app, url_for
from .token import generate_token

def _send_email(recipient, subject, body):
    """
    Internal helper function to send a plain text email.
    """
    app = current_app._get_current_object()
    msg = Message(
        subject,
        recipients=[recipient],
        body=body,
        sender=app.config['MAIL_DEFAULT_SENDER']
    )
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}") # For debugging
        return False

# --- ADD THIS NEW FUNCTION ---
def send_registration_email(recipient_email, username):
    """
    Builds and sends the initial welcome email with a verification link.
    """
    subject = "Welcome to Sayam's Bookmark App - Please Verify Your Email"
    
    # --- UPDATE THIS PART ---
    # 1. Generate a token containing the user's email
    token = generate_token(recipient_email)
    
    # 2. Create the full verification URL
    #    The `_external=True` is crucial to get the full domain name (e.g., http://127.0.0.1:5000/...)
    verification_url = url_for('auth.verify_email', token=token, _external=True)
    
    # 3. Build the email body with the real link
    body = f"""
Hello {username},

Welcome to Sayam's Bookmark App! We're excited to have you.

To complete your registration and activate your account, please click the link below:

{verification_url}

This link will expire in 1 hour.

If you did not sign up for this account, you can safely ignore this email.

Thanks,
The Sayam's Bookmark App Team
"""
    
    # Call the internal sending function
    return _send_email(recipient_email, subject, body)

# --- ADD THIS NEW FUNCTION ---
def send_verification_success_email(recipient_email, username):
    """
    Builds and sends an email confirming successful verification.
    """
    subject = "Your Account is Now Verified!"
    
    body = f"""
Hello {username},

This is a confirmation that your email address has been successfully verified.

You can now log in and start using all the features of Sayam's Bookmark App.

Welcome aboard!

Thanks,
The Sayam's Bookmark App Team
"""
    
    return _send_email(recipient_email, subject, body)

# --- ADD THIS NEW FUNCTION ---
def send_account_deletion_email(recipient_email, username):
    """
    Builds and sends an email confirming account deletion.
    """
    subject = "Your Sayam's Bookmark App Account Has Been Deleted"
    
    body = f"""
Hello {username},

This is a confirmation that your account with Sayam's Bookmark App has been successfully deleted. All of your associated data has been removed.

We're sorry to see you go. You are welcome back anytime.

Thanks,
The Sayam's Bookmark App Team
"""
    
    return _send_email(recipient_email, subject, body)

# --- MODIFY THIS FUNCTION ---
def send_collaborator_invitation_email(recipient_email, inviter_username, category_name, share_token):
    """
    Builds and sends an email notifying a user they've been added as a collaborator.
    """
    subject = f"You've been invited to collaborate on '{category_name}'"
    
    # This now creates a public, unauthenticated link using the share token.
    category_url = url_for('categories.get_shared_category', share_token=share_token, _external=True)
    
    body = f"""
Hello,

{inviter_username} has invited you to collaborate on the bookmark category: "{category_name}".

You can now view and add bookmarks to this category after logging in.

Click the link below to get a read-only preview of the category:
{category_url}

Thanks,
The Sayam's Bookmark App Team
"""
    
    return _send_email(recipient_email, subject, body)

# --- ADD THIS NEW FUNCTION ---
def send_password_reset_email(recipient_email, username, token):
    """
    Builds and sends an email with a password reset link.
    """
    subject = "Password Reset Request for Sayam's Bookmark App"
    
    # This will point to the new endpoint we are about to create.
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    body = f"""
Hello {username},

A request has been received to reset the password for your account.

Please click the link below to set a new password:
{reset_url}

This link will expire in 1 hour.

If you did not make this request, please ignore this email and your password will remain unchanged.

Thanks,
The Sayam's Bookmark App Team
"""
    
    return _send_email(recipient_email, subject, body)

# --- ADD THIS NEW FUNCTION ---
def send_password_reset_success_email(recipient_email, username):
    """
    Builds and sends an email confirming a successful password reset.
    """
    subject = "Your Password Has Been Changed"
    
    body = f"""
Hello {username},

This is a confirmation that the password for your Sayam's Bookmark App account has just been changed.

If you did not make this change, please secure your account and contact support immediately.

Thanks,
The Sayam's Bookmark App Team
"""
    
    return _send_email(recipient_email, subject, body)