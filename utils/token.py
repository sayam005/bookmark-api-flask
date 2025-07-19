from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def generate_token(data):
    """
    Generates a secure, timed token.
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(data, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration_seconds=3600):
    """
    Verifies a token and returns the original data if valid.
    Default expiration is 1 hour (3600 seconds).
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(
            token,
            salt=current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration_seconds
        )
        return data
    except Exception:
        # The exception could be SignatureExpired or BadTimeSignature.
        # We return None for any failure.
        return None