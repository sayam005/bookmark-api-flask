from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from config import db
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from utils.smtp import (send_registration_email, 
                        send_verification_success_email, 
                        send_account_deletion_email, 
                        send_password_reset_email,
                        send_password_reset_success_email)
from utils.token import confirm_token, generate_token
from flask import render_template_string

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, email, password]
          properties:
            username:
              type: string
              description: Username for the new user
            email:
              type: string
              description: Email for the new user
            password:
              type: string
              description: Password for the new user
    responses:
      201:
        description: User registered successfully
      400:
        description: Missing required fields
      409:
        description: User with this username or email already exists
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({'message': 'Username, email, and password are required'}), 400

    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters long'}), 400

    hashed_password = generate_password_hash(password)

    new_user = User(username=username, email=email, password_hash=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()

        send_registration_email(recipient_email=new_user.email, username=new_user.username)

        return jsonify({
            'message': f'User {username} created. Please check your email to verify your account.'
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        if 'UNIQUE constraint failed: user.username' in str(e.orig):
            return jsonify({'message': 'Username already exists'}), 409
        if 'UNIQUE constraint failed: user.email' in str(e.orig):
            return jsonify({'message': 'Email already exists'}), 409
        return jsonify({'message': 'Database integrity error'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT tokens
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, password]
          properties:
            username:
              type: string
              description: Username
            password:
              type: string
              description: Password
    responses:
      200:
        description: Logged in successfully
        schema:
          type: object
          properties:
            message:
              type: string
            access_token:
              type: string
            refresh_token:
              type: string
      401:
        description: Invalid username or password
      400:
        description: Missing required fields
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        return jsonify({
            'message': 'Logged in successfully',
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    return jsonify({'message': 'Invalid username or password'}), 401

@auth_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get the current user's profile
    ---
    tags:
      - User
    security:
      - Bearer: []
    responses:
      200:
        description: User profile details.
      404:
        description: User not found.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'created_at': user.created_at,
        'updated_at': user.updated_at
    }), 200

@auth_bp.route('/user', methods=['PATCH', 'DELETE'])
@jwt_required()
def manage_user():
    """Update or delete the current user's profile
    ---
    tags:
      - User
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        description: Required for PATCH. New username, email, and/or password.
        schema:
          type: object
          properties:
            username:
              type: string
            email:
              type: string
            password:
              type: string
    responses:
      200:
        description: User updated successfully.
      204:
        description: User account deleted successfully.
      404:
        description: User not found.
      409:
        description: Conflict (username or email already exists).
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    if request.method == 'DELETE':
        # We must capture the user's details before deleting them.
        user_email = user.email
        user_name = user.username
        
        db.session.delete(user)
        db.session.commit()
        
        # Send the confirmation email after the deletion is committed.
        send_account_deletion_email(recipient_email=user_email, username=user_name)
        
        return '', 204

    if request.method == 'PATCH':
        data = request.get_json()
        
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        
        if 'password' in data:
            user.set_password(data['password'])
        
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({'message': 'Username or email already in use'}), 409
            
        return jsonify({'message': 'User updated successfully'}), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Successfully logged out
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Successfully logged out"
      400:
        description: Bad request
        schema:
          type: object
          properties:
            msg:
              type: string
              example: "Bad Request"
      401:
        description: Invalid or missing token
        schema:
          type: object
          properties:
            msg:
              type: string
              example: "Missing Authorization Header"
    """
    try:
        return jsonify({'message': 'Successfully logged out'}), 200
    except Exception as e:
        return jsonify({'message': 'Logout failed', 'error': str(e)}), 400

@auth_bp.route('/verify', methods=['GET'])
def verify_email():
    """
    Verify user's email address from the token sent in the email.
    """
    token = request.args.get('token')
    if not token:
        return render_template_string("<h1>Error: Missing verification token.</h1>"), 400

    email = confirm_token(token)
    if not email:
        return render_template_string("<h1>Error: The verification link is invalid or has expired.</h1>"), 400

    user = User.query.filter_by(email=email).first_or_404()

    if user.is_verified:
        return render_template_string("<h1>Success: Your account has already been verified.</h1>"), 200
    else:
        user.is_verified = True
        db.session.add(user)
        db.session.commit()
        
        # After verifying, send the success email.
        send_verification_success_email(recipient_email=user.email, username=user.username)
        
        return render_template_string("<h1>Success! Your account has been verified.</h1><p>You can now log in.</p>"), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request a password reset email.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email]
          properties:
            email:
              type: string
              description: The email address of the user requesting the reset.
    responses:
      200:
        description: If a user with that email exists, a reset email has been sent.
    """
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'message': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()

    # IMPORTANT: For security, we always return a 200 OK response.
    # This prevents attackers from using this endpoint to check which emails are registered.
    if user:
        # Generate a token containing the user's email.
        token = generate_token(user.email)
        send_password_reset_email(user.email, user.username, token)

    return jsonify({'message': 'If an account with that email exists, a password reset link has been sent.'}), 200

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """
    Reset user's password. GET provides instructions, POST sets the new password.
    ---
    tags:
      - Authentication
    parameters:
      - in: query
        name: token
        type: string
        required: true
        description: The password reset token from the email link.
      - in: body
        name: body
        required: true
        description: Required for POST method.
        schema:
          type: object
          required: [password]
          properties:
            password:
              type: string
              description: The new password for the account.
    responses:
      200:
        description: Instructions for GET, or success message for POST.
      400:
        description: Bad request (e.g., token or password missing, password too short).
      401:
        description: The reset link is invalid or has expired.
    """
    token = request.args.get('token')
    if not token:
        return jsonify({'message': 'Reset token is missing'}), 400

    email = confirm_token(token)
    if not email:
        return jsonify({'message': 'The reset link is invalid or has expired'}), 401

    if request.method == 'GET':
        return jsonify({
            'message': 'Token is valid. To reset your password, make a POST request to this same URL.',
            'instructions': 'Include a JSON body with your new password.',
            'example_body': {'password': 'your-new-secure-password'}
        }), 200

    if request.method == 'POST':
        data = request.get_json()
        new_password = data.get('password')
        if not new_password:
            return jsonify({'message': 'New password is required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'message': 'Password must be at least 6 characters long'}), 400

        user = User.query.filter_by(email=email).first_or_404()

        user.set_password(new_password)
        db.session.commit()

        # --- ADD THIS LINE ---
        # Send a confirmation email after the password has been changed.
        send_password_reset_success_email(user.email, user.username)

        return jsonify({'message': 'Your password has been updated successfully.'}), 200