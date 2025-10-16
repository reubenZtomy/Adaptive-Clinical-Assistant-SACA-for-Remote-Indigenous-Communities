#!/usr/bin/env python3
"""
Script to view data in the SQLite database
"""
import sqlite3
import os
from datetime import datetime

def view_database():
    db_path = os.path.join('instance', 'swinsaca.db')
    
    if not os.path.exists(db_path):
        print("Database file not found!")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("SwinSACA Database Viewer")
        print("=" * 50)
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            return
        
        print(f"Found {len(tables)} table(s):")
        for table in tables:
            print(f"   - {table[0]}")
        
        print("\n" + "=" * 50)
        
        # View each table
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            print("-" * 30)
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            if columns:
                print("Columns:")
                for col in columns:
                    col_id, col_name, col_type, not_null, default_val, pk = col
                    pk_marker = " (PRIMARY KEY)" if pk else ""
                    null_marker = " NOT NULL" if not_null else ""
                    print(f"   - {col_name}: {col_type}{null_marker}{pk_marker}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            print(f"\nTotal rows: {row_count}")
            
            if row_count > 0:
                # Get all data
                cursor.execute(f"SELECT * FROM {table_name};")
                rows = cursor.fetchall()
                
                print(f"\nData:")
                for i, row in enumerate(rows, 1):
                    print(f"   Row {i}: {row}")
            else:
                print("   (No data)")
        
        conn.close()
        print(f"\nDatabase viewing completed!")
        
    except Exception as e:
        print(f"Error viewing database: {e}")

if __name__ == "__main__":
    view_database()