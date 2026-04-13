"""
Migrate passwords from plain-text to bcrypt hashes.

Handles BOTH teachers and students tables in a single run.
Already-hashed passwords (starting with $2b$) are skipped.

Usage:
    python migrate_passwords.py
"""

import sys
import os
import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logic'))
from db_config import get_connection


def migrate_table(table, id_col, name_col):
    """Generic password migration for any table."""
    connection = get_connection()
    if not connection:
        print("Failed to connect to database.")
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(f"SELECT {id_col}, {name_col}, password FROM {table}")
        rows = cursor.fetchall()
        
        print(f"\nFound {len(rows)} {table} accounts.")
        
        for row in rows:
            raw_password = row['password']
            
            # Skip if already a bcrypt hash
            if isinstance(raw_password, str) and raw_password.startswith("$2") and len(raw_password) >= 59:
                print(f"  {row[name_col]} — already hashed. Skipping.")
                continue
            
            hashed = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(f"UPDATE {table} SET password = %s WHERE {id_col} = %s", (hashed, row[id_col]))
            print(f"  Migrated {row[name_col]} ({row[id_col]}) successfully.")
            
        connection.commit()
        print(f"{table} migration complete!")
        
    except Exception as e:
        print(f"Error during {table} migration: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    migrate_table("teachers", "teacher_id", "teacher_name")
    migrate_table("students", "student_id", "student_name")
