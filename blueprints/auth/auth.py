from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token, get_jwt
from models import User
from config import db
from sqlalchemy.exc import IntegrityError

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

    if not username or not email or not password:
        return jsonify({'message': 'Username, email, and password are required'}), 400

    # Check if user already exists
    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({'message': 'User with this username or email already exists'}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'User with this username or email already exists'}), 409

    return jsonify({'message': 'User registered successfully'}), 201

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
        return jsonify({"message": "User not found"}), 404

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

    if request.method == 'DELETE':
        db.session.delete(user)
        db.session.commit()
        return '', 204

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
        # Simple logout - just return success message
        # In a simple setup, we rely on frontend to discard the token
        return jsonify({'message': 'Successfully logged out'}), 200
    except Exception as e:
        return jsonify({'message': 'Logout failed', 'error': str(e)}), 400