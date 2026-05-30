"""
Create MySQL database for ParkHub
Run this before initializing the database
"""
import pymysql
import os
from pathlib import Path

# Try to load from .env file
def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / '.env'
    config = {
        'DB_HOST': 'localhost',
        'DB_PORT': '3306',
        'DB_USER': 'root',
        'DB_PASSWORD': '',
        'DB_NAME': 'parkhub_db'
    }
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    return config

config = load_env()

DB_HOST = config['DB_HOST']
DB_PORT = int(config['DB_PORT'])
DB_USER = config['DB_USER']
DB_PASSWORD = config['DB_PASSWORD']
DB_NAME = config['DB_NAME']

def create_database():
    """Create the ParkHub database if it doesn't exist"""
    
    print(f"🔌 Connecting to MySQL at {DB_HOST}:{DB_PORT} as user '{DB_USER}'...")
    
    # If password is empty, try common defaults
    passwords_to_try = [DB_PASSWORD]
    if not DB_PASSWORD:
        passwords_to_try.extend(['root', 'password', ''])
    
    connection = None
    last_error = None
    
    for pwd in passwords_to_try:
        try:
            print(f"   Trying password: {'(empty)' if not pwd else '***'}")
            connection = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=pwd
            )
            print(f"   ✅ Connected successfully!")
            break
        except pymysql.err.OperationalError as e:
            last_error = e
            if '1045' in str(e):  # Access denied
                continue
            else:
                raise
    
    if not connection:
        print(f"\n❌ Could not connect to MySQL!")
        print(f"\n💡 Please update your MySQL password in .env file:")
        print(f"   1. Copy .env.example to .env")
        print(f"   2. Set DB_PASSWORD=your_mysql_password")
        print(f"\n   To find your password, try:")
        print(f"   mysql -u root -p")
        raise last_error
    
    try:
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        print(f"🗄️  Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        print(f"✅ Database '{DB_NAME}' is ready!")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise


if __name__ == "__main__":
    create_database()
