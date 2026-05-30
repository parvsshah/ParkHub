"""
Database initialization script
Creates all tables directly from SQL
"""
import psycopg2
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

def init_database():
    """Initialize database by creating all tables"""
    print("🔧 Initializing database...")
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Drop existing indexes and tables
        print("⚠️  Dropping existing tables and indexes...")
        cursor.execute("DROP INDEX IF EXISTS idx_users_email")
        cursor.execute("DROP INDEX IF EXISTS idx_parking_lots_city")
        cursor.execute("DROP INDEX IF EXISTS idx_parking_lots_pin_code")
        cursor.execute("DROP INDEX IF EXISTS idx_parking_spots_lot_id")
        cursor.execute("DROP INDEX IF EXISTS idx_parking_spots_status")
        cursor.execute("DROP INDEX IF EXISTS idx_bookings_user_id")
        cursor.execute("DROP INDEX IF EXISTS idx_bookings_lot_id")
        cursor.execute("DROP INDEX IF EXISTS idx_bookings_spot_id")
        cursor.execute("DROP INDEX IF EXISTS idx_bookings_status")
        cursor.execute("DROP INDEX IF EXISTS idx_payments_booking_id")
        cursor.execute("DROP INDEX IF EXISTS idx_audit_logs_action_type")
        cursor.execute("DROP INDEX IF EXISTS idx_audit_logs_timestamp")
        cursor.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
        cursor.execute("DROP TABLE IF EXISTS payments CASCADE")
        cursor.execute("DROP TABLE IF EXISTS bookings CASCADE")
        cursor.execute("DROP TABLE IF EXISTS parking_spots CASCADE")
        cursor.execute("DROP TABLE IF EXISTS parking_lots CASCADE")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE")
        
        # Create users table
        print("📊 Creating users table...")
        cursor.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                address TEXT,
                pin_code VARCHAR(20),
                vehicle_number VARCHAR(50),
                wallet_balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                role VARCHAR(10) NOT NULL DEFAULT 'USER' CHECK (role IN ('USER', 'ADMIN')),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_users_email ON users(email)")
        
        # Create parking_lots table
        print("📊 Creating parking_lots table...")
        cursor.execute("""
            CREATE TABLE parking_lots (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                address TEXT NOT NULL,
                city VARCHAR(100) NOT NULL,
                pin_code VARCHAR(20) NOT NULL,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                total_spots INT NOT NULL,
                hourly_rate DECIMAL(10, 2) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_parking_lots_city ON parking_lots(city)")
        cursor.execute("CREATE INDEX idx_parking_lots_pin_code ON parking_lots(pin_code)")
        
        # Create parking_spots table
        print("📊 Creating parking_spots table...")
        cursor.execute("""
            CREATE TABLE parking_spots (
                id SERIAL PRIMARY KEY,
                lot_id INT NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
                spot_code VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE', 'OCCUPIED', 'RESERVED', 'OUT_OF_SERVICE')),
                current_booking_id INT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_parking_spots_lot_id ON parking_spots(lot_id)")
        cursor.execute("CREATE INDEX idx_parking_spots_status ON parking_spots(status)")
        
        # Create bookings table
        print("📊 Creating bookings table...")
        cursor.execute("""
            CREATE TABLE bookings (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                lot_id INT NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
                spot_id INT NOT NULL REFERENCES parking_spots(id) ON DELETE CASCADE,
                vehicle_number VARCHAR(50) NOT NULL,
                start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration_minutes INT,
                duration_hours INT,
                hourly_rate DECIMAL(10, 2),
                total_cost DECIMAL(10, 2),
                status VARCHAR(10) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'COMPLETED', 'CANCELLED')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_bookings_user_id ON bookings(user_id)")
        cursor.execute("CREATE INDEX idx_bookings_lot_id ON bookings(lot_id)")
        cursor.execute("CREATE INDEX idx_bookings_spot_id ON bookings(spot_id)")
        cursor.execute("CREATE INDEX idx_bookings_status ON bookings(status)")
        
        # Create payments table
        print("📊 Creating payments table...")
        cursor.execute("""
            CREATE TABLE payments (
                id SERIAL PRIMARY KEY,
                booking_id INT NOT NULL UNIQUE REFERENCES bookings(id) ON DELETE CASCADE,
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(10) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED')),
                provider VARCHAR(50),
                transaction_ref VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vehicles table
        print("📊 Creating vehicles table...")
        cursor.execute("""
            CREATE TABLE vehicles (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                vehicle_number VARCHAR(50) NOT NULL,
                vehicle_type VARCHAR(50),
                color VARCHAR(50),
                is_primary BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_vehicles_user_id ON vehicles(user_id)")
        
        # Create audit_logs table
        print("📊 Creating audit_logs table...")
        cursor.execute("""
            CREATE TABLE audit_logs (
                id SERIAL PRIMARY KEY,
                actor_id INT REFERENCES users(id) ON DELETE SET NULL,
                actor_role VARCHAR(50),
                action_type VARCHAR(100) NOT NULL,
                entity_type VARCHAR(100) NOT NULL,
                entity_id INT,
                meta JSONB,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_action_type ON audit_logs(action_type)")
        cursor.execute("CREATE INDEX idx_timestamp ON audit_logs(timestamp)")
        
        # Add foreign key for parking_spots.current_booking_id
        cursor.execute("""
            ALTER TABLE parking_spots 
            ADD CONSTRAINT fk_current_booking 
            FOREIGN KEY (current_booking_id) REFERENCES bookings(id) ON DELETE SET NULL
        """)
        
        conn.commit()
        
        print("✅ Database initialized successfully!")
        print("\nTables created:")
        print("  - users")
        print("  - parking_lots")
        print("  - parking_spots")
        print("  - bookings")
        print("  - payments")
        print("  - audit_logs")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_database()
