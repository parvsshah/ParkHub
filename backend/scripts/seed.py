"""
Database seed script - populate with sample data
"""
import psycopg2
import bcrypt
from decimal import Decimal
from pathlib import Path

# Try to load from .env file
def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / '.env'
    config = {}
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

    if 'DATABASE_URL' not in config:
        config['DATABASE_URL'] = os.environ.get('DATABASE_URL')

    if not config.get('DATABASE_URL'):
        raise RuntimeError('DATABASE_URL must be set in .env or environment variables')
    
    return config

config = load_env()

DATABASE_URL = config['DATABASE_URL']

def hash_password(password):
    """Secure password hashing using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def seed_database():
    """Seed the database with initial data"""
    print("🌱 Seeding database...")
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Create admin user
        print("👤 Creating admin user...")
        cursor.execute("""
            INSERT INTO users (name, email, hashed_password, role, is_active)
            VALUES (%s, %s, %s, 'ADMIN', TRUE)
            ON CONFLICT (email) DO UPDATE SET 
                name = EXCLUDED.name,
                hashed_password = EXCLUDED.hashed_password,
                role = EXCLUDED.role
        """, ('Admin User', 'admin@parkhub.com', hash_password('admin123456')))
        
        # Create sample users
        print("👥 Creating sample users...")
        sample_users = [
            ('User 1', 'user1@parkhub.com', 'password123', '123 Main St, Mumbai', '400001', 'MH01AB1234'),
            ('User 2', 'user2@parkhub.com', 'password123', '456 Park Ave, Mumbai', '400002', 'MH02CD5678')
        ]
        
        for name, email, password, address, pin_code, vehicle in sample_users:
            cursor.execute("""
                INSERT INTO users (name, email, hashed_password, address, pin_code, vehicle_number, role)
                VALUES (%s, %s, %s, %s, %s, %s, 'USER')
                ON CONFLICT (email) DO UPDATE SET 
                    name = EXCLUDED.name,
                    hashed_password = EXCLUDED.hashed_password,
                    address = EXCLUDED.address,
                    pin_code = EXCLUDED.pin_code,
                    vehicle_number = EXCLUDED.vehicle_number
            """, (name, email, hash_password(password), address, pin_code, vehicle))
        
        conn.commit()
        
        # Create sample parking lots
        print("🅿️  Creating sample parking lots...")
        sample_lots = [
            ('Downtown Plaza Parking', '123 MG Road, Fort', 'Mumbai', '400001', 18.9388, 72.8354, 50, Decimal('50.00')),
            ('Bandra West Parking Hub', '456 Linking Road, Bandra West', 'Mumbai', '400050', 19.0596, 72.8295, 75, Decimal('60.00')),
            ('Andheri Station Parking', '789 SV Road, Andheri East', 'Mumbai', '400069', 19.1136, 72.8697, 100, Decimal('40.00')),
            ('Powai Tech Park Parking', '321 Hiranandani Gardens, Powai', 'Mumbai', '400076', 19.1197, 72.9073, 120, Decimal('45.00'))
        ]
        
        for lot_data in sample_lots:
            # Check if lot already exists
            cursor.execute("SELECT id FROM parking_lots WHERE name = %s", (lot_data[0],))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute("""
                    INSERT INTO parking_lots (name, address, city, pin_code, latitude, longitude, total_spots, hourly_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, lot_data)
                
                lot_id = cursor.fetchone()[0]
                total_spots = lot_data[6]
                
                # Create parking spots
                print(f"   Creating {total_spots} spots for {lot_data[0]}...")
                for i in range(1, total_spots + 1):
                    section = chr(65 + (i - 1) // 50)  # A, B, C, etc.
                    number = (i - 1) % 50 + 1
                    spot_code = f"{section}-{number:02d}"
                    
                    cursor.execute("""
                        INSERT INTO parking_spots (lot_id, spot_code, status)
                        VALUES (%s, %s, 'AVAILABLE')
                    """, (lot_id, spot_code))
                
                print(f"   ✅ Created {lot_data[0]} with {total_spots} spots")
        
        conn.commit()
        
        print("\n✅ Database seeded successfully!")
        print("\n📝 Demo Credentials:")
        print("   Admin: admin@parkhub.com / admin123456")
        print("   User:  user1@parkhub.com / password123")
        print("   User:  user2@parkhub.com / password123")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    seed_database()
