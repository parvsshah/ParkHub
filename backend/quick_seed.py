#!/usr/bin/env python3
"""Quick database seeding"""
import os
import psycopg2
from pathlib import Path
import bcrypt

env_file = Path('.env')
config = {}

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                config[key.strip()] = val.strip()

if 'DATABASE_URL' not in config:
    config['DATABASE_URL'] = os.environ.get('DATABASE_URL')

if not config.get('DATABASE_URL'):
    raise RuntimeError('DATABASE_URL must be set in .env or environment variables')

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

conn = psycopg2.connect(config['DATABASE_URL'])
cursor = conn.cursor()

try:
    # Create admin user
    cursor.execute("""
        INSERT INTO users (name, email, hashed_password, address, pin_code, vehicle_number, wallet_balance, role)
        VALUES (%s, %s, %s, %s, %s, %s, 1000.00, 'ADMIN')
        ON CONFLICT (email) DO NOTHING
    """, (
        'Admin User',
        'admin@parkhub.com',
        hash_password('admin123456'),
        '123 Admin St',
        '110001',
        'ADM001'
    ))
    
    # Create test user
    cursor.execute("""
        INSERT INTO users (name, email, hashed_password, address, pin_code, vehicle_number, wallet_balance, role)
        VALUES (%s, %s, %s, %s, %s, %s, 500.00, 'USER')
        ON CONFLICT (email) DO NOTHING
    """, (
        'Test User',
        'user1@parkhub.com',
        hash_password('password123'),
        '456 User Ave',
        '110002',
        'KA01AB1234'
    ))
    
    # Create a parking lot
    cursor.execute("""
        INSERT INTO parking_lots (name, address, city, pin_code, total_spots, hourly_rate)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        'Downtown Plaza Parking',
        '123 Main Street',
        'New Delhi',
        '110001',
        50,
        50.00
    ))
    
    lot_id = cursor.fetchone()[0]
    
    # Create parking spots for the lot
    for i in range(1, 51):
        section = chr(65 + (i - 1) // 50)
        number = (i - 1) % 50 + 1
        spot_code = f"{section}-{number:02d}"
        cursor.execute("""
            INSERT INTO parking_spots (lot_id, spot_code, status)
            VALUES (%s, %s, 'AVAILABLE')
        """, (lot_id, spot_code))
    
    conn.commit()
    print("✅ Database seeded successfully!")
    print(f"   - Admin user created")
    print(f"   - Test user created")
    print(f"   - {lot_id} parking lot created with 50 spots")
    
except Exception as e:
    conn.rollback()
    print(f"⚠️ Error: {e}")
finally:
    cursor.close()
    conn.close()
