#!/usr/bin/env python3
import psycopg2
from pathlib import Path

env_file = Path('.env')
config = {
    'DATABASE_URL': 'postgresql://neondb_owner:npg_8stLa3kcZVMe@ep-muddy-bar-ad912ml9-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
}

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                config[key.strip()] = val.strip()

conn = psycopg2.connect(config['DATABASE_URL'])
cursor = conn.cursor()

# Check if users table exists and has wallet_balance column
cursor.execute("""
SELECT column_name FROM information_schema.columns 
WHERE table_name='users' ORDER BY column_name
""")
print('Users table columns:', [row[0] for row in cursor.fetchall()])

# Check if bookings table has duration_hours
cursor.execute("""
SELECT column_name FROM information_schema.columns 
WHERE table_name='bookings' ORDER BY column_name
""")
print('Bookings table columns:', [row[0] for row in cursor.fetchall()])

# Check number of users
cursor.execute("SELECT COUNT(*) FROM users")
print('Number of users:', cursor.fetchone()[0])

# Check number of parking lots
cursor.execute("SELECT COUNT(*) FROM parking_lots")
print('Number of parking lots:', cursor.fetchone()[0])

conn.close()
print("\n✅ Schema verification complete!")
