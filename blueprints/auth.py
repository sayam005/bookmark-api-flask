from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import create_access_token, create_refresh_token
from models import User
from app import db

# Create a namespace for authentication
auth_ns = Namespace('auth', description='Authentication related operations')

# Define the data model for user signup
signup_model = auth_ns.model('SignUp', {
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password'),
})

# Define the data model for user login
login_model = auth_ns.model('Login', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
})

@auth_ns.route('/register')
class SignUp(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        """Create a new user"""
        data = request.get_json()

        # Check if user already exists
        if User.query.filter_by(username=data.get('username')).first() or \
           User.query.filter_by(email=data.get('email')).first():
            return {'message': 'User with this username or email already exists'}, 409

        new_user = User(
            username=data.get('username'),
            email=data.get('email')
        )
        new_user.set_password(data.get('password'))

        db.session.add(new_user)
        db.session.commit()

        return {'message': 'User created successfully'}, 201

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Login a user and return tokens"""
        data = request.get_json()
        user = User.query.filter_by(username=data.get('username')).first()

        if user and user.check_password(data.get('password')):
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            return {
                'message': 'Logged in successfully',
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 200

        return {'message': 'Invalid username or password'}, 401