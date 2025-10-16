#!/usr/bin/env python3
"""
Setup script for SwinSACA Flask Backend
Run this script to initialize the database and start the server
"""

import os
import sys
from app import app, db

def setup_database():
    """Create database tables"""
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
    print("Database tables created successfully!")

def main():
    print("SwinSACA Flask Backend Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  .env file not found!")
        print("Please create a .env file based on env_example.txt")
        print("Update the DATABASE_URL with your phpMyAdmin credentials")
        return
    
    # Setup database
    try:
        setup_database()
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("Please check your DATABASE_URL in the .env file")
        return
    
    print("\n✅ Setup completed successfully!")
    print("\nTo start the server, run:")
    print("python app.py")
    print("\nThen visit:")
    print("- API: http://localhost:5000/api/")
    print("- Swagger UI: http://localhost:5000/api/swagger/")

if __name__ == "__main__":
    main()


