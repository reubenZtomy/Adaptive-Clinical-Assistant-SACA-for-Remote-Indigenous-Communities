from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
import models
from models import User
import re

# Create namespace for authentication
auth_ns = Namespace('auth', description='Authentication operations')

# Define models for Swagger documentation
login_model = auth_ns.model('Login', {
    'username': fields.String(required=True, description='Username or email'),
    'password': fields.String(required=True, description='Password')
})

register_model = auth_ns.model('Register', {
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email address'),
    'password': fields.String(required=True, description='Password'),
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name')
})

user_model = auth_ns.model('User', {
    'id': fields.Integer(description='User ID'),
    'username': fields.String(description='Username'),
    'email': fields.String(description='Email address'),
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name'),
    'is_active': fields.Boolean(description='User active status'),
    'created_at': fields.String(description='Creation date')
})

token_model = auth_ns.model('Token', {
    'access_token': fields.String(description='JWT access token'),
    'user': fields.Nested(user_model, description='User information')
})

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    @auth_ns.marshal_with(token_model)
    def post(self):
        """Register a new user"""
        data = request.get_json()
        print(f"Registration request received: {data}")
        
        # Validate required fields
        if not data.get('username') or not data.get('email') or not data.get('password'):
            print("Missing required fields")
            return {'message': 'Username, email, and password are required'}, 400
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            return {'message': 'Invalid email format'}, 400
        
        # Validate password strength
        if len(data['password']) < 6:
            return {'message': 'Password must be at least 6 characters long'}, 400
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return {'message': 'Username already exists'}, 400
        
        if User.query.filter_by(email=data['email']).first():
            return {'message': 'Email already exists'}, 400
        
        try:
            # Create new user
            user = User(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data.get('first_name'),
                last_name=data.get('last_name')
            )
            
            models.db.session.add(user)
            models.db.session.commit()
            
            # Generate token
            access_token = user.generate_token()
            
            print(f"User created successfully: {user.username}")
            return {
                'access_token': access_token,
                'user': user.to_dict()
            }, 201
            
        except Exception as e:
            print(f"Registration error: {e}")
            models.db.session.rollback()
            return {'message': f'Registration failed: {str(e)}'}, 500

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(token_model)
    def post(self):
        """Login user"""
        data = request.get_json()
        print(f"Login request received: {data}")
        
        if not data.get('username') or not data.get('password'):
            print("Missing username or password")
            return {'message': 'Username and password are required'}, 400
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == data['username']) | (User.email == data['username'])
        ).first()
        
        print(f"User found: {user.username if user else 'None'}")
        
        if not user or not user.check_password(data['password']):
            print("Invalid credentials")
            return {'message': 'Invalid credentials'}, 401
        
        if not user.is_active:
            return {'message': 'Account is deactivated'}, 401
        
        # Generate token
        access_token = user.generate_token()
        
        print(f"Login successful for user: {user.username}")
        return {
            'access_token': access_token,
            'user': user.to_dict()
        }, 200

@auth_ns.route('/profile')
class Profile(Resource):
    @jwt_required()
    @auth_ns.marshal_with(user_model)
    def get(self):
        """Get current user profile"""
        try:
            current_user_id = get_jwt_identity()
            print(f"Profile request for user ID: {current_user_id}")
            
            user = User.query.get(current_user_id)
            
            if not user:
                print(f"User not found for ID: {current_user_id}")
                return {'message': 'User not found'}, 404
            
            print(f"Profile data for user: {user.username}")
            return user.to_dict(), 200
        except Exception as e:
            print(f"Profile endpoint error: {e}")
            return {'message': f'Profile error: {str(e)}'}, 500
    
    @jwt_required()
    @auth_ns.expect(register_model)
    @auth_ns.marshal_with(user_model)
    def put(self):
        """Update user profile"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return {'message': 'User not found'}, 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            # Validate email format
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, data['email']):
                return {'message': 'Invalid email format'}, 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user.id:
                return {'message': 'Email already exists'}, 400
            
            user.email = data['email']
        
        try:
            models.db.session.commit()
            return user.to_dict(), 200
        except Exception as e:
            models.db.session.rollback()
            return {'message': 'Update failed'}, 500

@auth_ns.route('/verify')
class Verify(Resource):
    @jwt_required()
    def get(self):
        """Verify JWT token"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return {'message': 'Invalid token'}, 401
        
        return {'message': 'Token is valid', 'user': user.to_dict()}, 200
