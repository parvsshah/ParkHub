#!/usr/bin/env python3
"""Simple parking lot seeder"""
import os
import psycopg2
from pathlib import Path

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
    # Create parking lots
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
        
        # Create spots
        for i in range(1, spots + 1):
            section = chr(65 + (i - 1) // 50)
            number = (i - 1) % 50 + 1
            spot_code = f"{section}-{number:02d}"
            cursor.execute("""
                INSERT INTO parking_spots (lot_id, spot_code, status)
                VALUES (%s, %s, 'AVAILABLE')
            """, (lot_id, spot_code))
        
        print(f"✅ Created: {name} ({spots} spots)")
    
    conn.commit()
    print("\n✅ Database seeded successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
