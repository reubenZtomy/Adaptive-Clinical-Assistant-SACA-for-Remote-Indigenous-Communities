#!/usr/bin/env python3
"""
Database management script for SwinSACA
"""
import sqlite3
import os
import sys
from datetime import datetime

def connect_db():
    """Connect to the database"""
    db_path = os.path.join('instance', 'swinsaca.db')
    if not os.path.exists(db_path):
        print("Database file not found!")
        return None
    return sqlite3.connect(db_path)

def show_users():
    """Show all users in a formatted way"""
    conn = connect_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC;")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"Found {len(users)} user(s):")
        print("=" * 80)
        
        for user in users:
            id, username, email, password_hash, first_name, last_name, is_active, created_at, updated_at = user
            
            print(f"ID: {id}")
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Name: {first_name or 'N/A'} {last_name or 'N/A'}")
            print(f"Active: {'Yes' if is_active else 'No'}")
            print(f"Created: {created_at}")
            print(f"Updated: {updated_at}")
            print(f"Password Hash: {password_hash[:20]}...")
            print("-" * 40)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def add_test_user():
    """Add a test user to the database"""
    conn = connect_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        # Check if test user already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", ('testuser',))
        if cursor.fetchone():
            print("Test user already exists!")
            return
        
        # Add test user
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, first_name, last_name, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'testuser',
            'test@example.com',
            'hashed_password_here',
            'Test',
            'User',
            True,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        print("Test user added successfully!")
        
    except Exception as e:
        print(f"Error adding test user: {e}")
        conn.rollback()
    finally:
        conn.close()

def delete_user(username):
    """Delete a user by username"""
    conn = connect_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        if cursor.rowcount > 0:
            conn.commit()
            print(f"User '{username}' deleted successfully!")
        else:
            print(f"User '{username}' not found!")
        
    except Exception as e:
        print(f"Error deleting user: {e}")
        conn.rollback()
    finally:
        conn.close()

def show_help():
    """Show help information"""
    print("SwinSACA Database Manager")
    print("=" * 30)
    print("Commands:")
    print("  python db_manager.py users     - Show all users")
    print("  python db_manager.py add       - Add test user")
    print("  python db_manager.py delete    - Delete user (interactive)")
    print("  python db_manager.py help      - Show this help")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'users':
        show_users()
    elif command == 'add':
        add_test_user()
    elif command == 'delete':
        username = input("Enter username to delete: ")
        delete_user(username)
    elif command == 'help':
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main()


