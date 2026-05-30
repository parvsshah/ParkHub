#!/usr/bin/env python3
import os
import psycopg2
import bcrypt
from pathlib import Path

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

config = {}

env_file = Path('.env')
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

conn = psycopg2.connect(config['DATABASE_URL'])
cursor = conn.cursor()

try:
    # Check if users already exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Create users
        cursor.execute("""
            INSERT INTO users (name, email, hashed_password, address, pin_code, vehicle_number, wallet_balance, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            'Admin User',
            'admin@parkhub.com',
            hash_password('admin123456'),
            '123 Admin St',
            '110001',
            'ADM001',
            1000.00,
            'ADMIN'
        ))
        
        # Create test user
        cursor.execute("""
            INSERT INTO users (name, email, hashed_password, address, pin_code, vehicle_number, wallet_balance, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            'Test User',
            'user1@parkhub.com',
            hash_password('password123'),
            '456 User Ave',
            '110002',
            'KA01AB1234',
            500.00,
            'USER'
        ))
        
        print("✅ Users created")
    
    # Check if parking lots exist
    cursor.execute("SELECT COUNT(*) FROM parking_lots")
    lot_count = cursor.fetchone()[0]
    
    if lot_count == 0:
        # Create lots
        lots = [
            ('Downtown Plaza Parking', '123 Main Street', 'New Delhi', '110001', 50, 50.00),
            ('Airport Parking Hub', '456 Airport Road', 'New Delhi', '110037', 100, 75.00),
            ('Mall Parking Center', '789 Shopping District', 'New Delhi', '110088', 75, 40.00),
        ]
        
        for name, address, city, pin, spots, rate in lots:
            cursor.execute("""
                INSERT INTO parking_lots (name, address, city, pin_code, total_spots, hourly_rate)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, address, city, pin, spots, rate))
            
            lot_id = cursor.fetchone()[0]
            
            for i in range(1, spots + 1):
                section = chr(65 + (i - 1) // 50)
                number = (i - 1) % 50 + 1
                spot_code = f"{section}-{number:02d}"
                cursor.execute("""
                    INSERT INTO parking_spots (lot_id, spot_code, status)
                    VALUES (%s, %s, 'AVAILABLE')
                """, (lot_id, spot_code))
            
            print(f"✅ Created: {name} ({spots} spots)")
    else:
        print(f"✅ {lot_count} parking lots already exist")
    
    conn.commit()
    print("✅ Database seeded successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
