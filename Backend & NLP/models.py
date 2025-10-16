from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import bcrypt

# This will be set by app.py
db = None

def create_models(database):
    """Create models with the provided database instance"""
    global db
    db = database
    
    class User(db.Model):
        __tablename__ = 'users'
        
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False, index=True)
        email = db.Column(db.String(120), unique=True, nullable=False, index=True)
        password_hash = db.Column(db.String(255), nullable=False)
        first_name = db.Column(db.String(50), nullable=True)
        last_name = db.Column(db.String(50), nullable=True)
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        def __init__(self, username, email, password, first_name=None, last_name=None):
            self.username = username
            self.email = email
            self.set_password(password)
            self.first_name = first_name
            self.last_name = last_name
        
        def set_password(self, password):
            """Hash and set password"""
            self.password_hash = generate_password_hash(password)
        
        def check_password(self, password):
            """Check if provided password matches hash"""
            return check_password_hash(self.password_hash, password)
        
        def generate_token(self):
            """Generate JWT token for user"""
            return create_access_token(identity=self.id)
        
        def to_dict(self):
            """Convert user to dictionary"""
            return {
                'id': self.id,
                'username': self.username,
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'is_active': self.is_active,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        
        def __repr__(self):
            return f'<User {self.username}>'
    
    return User

# Global User class will be set after create_models is called
User = None