from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
import models
from models import User, Prediction
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
            current_user_id = int(get_jwt_identity())
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
        current_user_id = int(get_jwt_identity())
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
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return {'message': 'Invalid token'}, 401
        
        return {'message': 'Token is valid', 'user': user.to_dict()}, 200

# Prediction History endpoints
@auth_ns.route('/predictions')
class Predictions(Resource):
    @jwt_required()
    def get(self):
        """Get user's prediction history"""
        try:
            current_user_id = int(get_jwt_identity())
            user = User.query.get(current_user_id)
            
            if not user:
                return {'message': 'User not found'}, 404
            
            # Get all predictions for the user, ordered by most recent first
            predictions = Prediction.query.filter_by(user_id=current_user_id).order_by(Prediction.created_at.desc()).all()
            
            return {
                'predictions': [pred.to_dict() for pred in predictions],
                'count': len(predictions)
            }, 200
            
        except Exception as e:
            print(f"Error fetching predictions: {e}")
            return {'message': f'Error fetching predictions: {str(e)}'}, 500

@auth_ns.route('/predictions/<int:prediction_id>')
class PredictionDetail(Resource):
    @jwt_required()
    def delete(self, prediction_id):
        """Delete a specific prediction"""
        try:
            current_user_id = int(get_jwt_identity())
            user = User.query.get(current_user_id)
            
            if not user:
                return {'message': 'User not found'}, 404
            
            # Find the prediction and verify it belongs to the user
            prediction = Prediction.query.filter_by(id=prediction_id, user_id=current_user_id).first()
            
            if not prediction:
                return {'message': 'Prediction not found or access denied'}, 404
            
            # Delete the prediction
            models.db.session.delete(prediction)
            models.db.session.commit()
            
            return {'message': 'Prediction deleted successfully'}, 200
            
        except Exception as e:
            print(f"Error deleting prediction: {e}")
            models.db.session.rollback()
            return {'message': f'Error deleting prediction: {str(e)}'}, 500
