from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token
from models import User
from extensions import db

# Create a blueprint for authentication
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
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              description: Username for the new user
            email:
              type: string
              format: email
              description: Email address for the new user
            password:
              type: string
              description: Password for the new user
    responses:
      201:
        description: User created successfully
        schema:
          type: object
          properties:
            message:
              type: string
      409:
        description: User with this username or email already exists
        schema:
          type: object
          properties:
            message:
              type: string
      400:
        description: Missing required fields
        schema:
          type: object
          properties:
            message:
              type: string
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No JSON data provided'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({'message': 'Username, email, and password are required'}), 400

    # Check if user already exists
    if User.query.filter_by(username=username).first() or \
       User.query.filter_by(email=email).first():
        return jsonify({'message': 'User with this username or email already exists'}), 409

    new_user = User(
        username=username,
        email=email
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user and return tokens
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
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
        schema:
          type: object
          properties:
            message:
              type: string
      400:
        description: Missing required fields
        schema:
          type: object
          properties:
            message:
              type: string
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No JSON data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return jsonify({'message': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        return jsonify({
            'message': 'Logged in successfully',
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200

    return jsonify({'message': 'Invalid username or password'}), 401