"""
ParkHub - Unified Server (Backend API + Frontend)
Single Flask server serving both API and static files
"""
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import bcrypt
import redis
import secrets
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
import os
import re

# Get the directory paths
BACKEND_DIR = Path(__file__).parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / 'html-version'

# Create Flask app with static folder pointing to frontend
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path='')
CORS(app)

# Load configuration from .env
def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / '.env'
    config = {
        'DATABASE_URL': 'postgresql://neondb_owner:npg_8stLa3kcZVMe@ep-muddy-bar-ad912ml9-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
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

# Database Configuration
DATABASE_URL = config['DATABASE_URL']

JWT_SECRET = 'your-secret-key-change-in-production'

# Set up logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to connect to Redis
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()  # Test connection
    logger.info("Redis connected successfully")
except redis.ConnectionError:
    logger.warning("Redis not available, using in-memory token storage")
    redis_client = None

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    return True, None

# Database Helper
def get_db():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def hash_password(password):
    """Secure password hashing using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def generate_token():
    """Generate a simple token"""
    return secrets.token_urlsafe(32)

# In-memory token storage as fallback
token_storage = {}

def store_token(token, user_data, ttl_seconds=3600):
    """Store token with user data"""
    if redis_client:
        redis_client.setex(token, ttl_seconds, json.dumps(user_data))
    else:
        token_storage[token] = user_data
        # In a real app, you'd want to implement TTL for in-memory storage too

def get_token_data(token):
    """Get user data from token"""
    if redis_client:
        user_data = redis_client.get(token)
        return json.loads(user_data) if user_data else None
    else:
        return token_storage.get(token)

# Auth Decorator
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = get_token_data(token)
        if not token or not user_data:
            return jsonify({'error': 'Unauthorized'}), 401
        request.user = user_data
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_data = get_token_data(token)
        if not token or not user_data:
            return jsonify({'error': 'Unauthorized'}), 401
        user = user_data
        if user['role'] != 'ADMIN':
            return jsonify({'error': 'Admin access required'}), 403
        request.user = user
        return f(*args, **kwargs)
    return decorated

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.json
    
    # Validate input
    if not data.get('email') or not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if not data.get('password'):
        return jsonify({'error': 'Password is required'}), 400
    
    valid, msg = validate_password(data['password'])
    if not valid:
        return jsonify({'error': msg}), 400
    
    if not data.get('name') or len(data['name']) < 2:
        return jsonify({'error': 'Name must be at least 2 characters'}), 400
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Check if email exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (data['email'],))
        if cursor.fetchone():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (name, email, hashed_password, address, pin_code, vehicle_number, role, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'USER', NOW(), NOW())
        """, (
            data['name'],
            data['email'],
            hash_password(data['password']),
            data.get('address'),
            data.get('pin_code'),
            data.get('vehicle_number')
        ))
        conn.commit()
        user_id = cursor.lastrowid
        
        # Get user
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        # Generate token
        token = generate_token()
        # Store safe user data in Redis (exclude sensitive fields and datetime objects)
        safe_user = {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'address': user.get('address'),
            'pin_code': user.get('pin_code'),
            'vehicle_number': user.get('vehicle_number')
        }
        store_token(token, safe_user, 3600)  # 1 hour TTL
        
        return jsonify({
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'role': user['role']
            },
            'access_token': token,
            'refresh_token': token,
            'token_type': 'bearer'
        }), 201
        
    except Exception as e:
        logger.exception("Registration error")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
        user = cursor.fetchone()
        
        if not user or not bcrypt.checkpw(data['password'].encode(), user['hashed_password'].encode()):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate token
        token = generate_token()
        # Store safe user data in Redis (exclude sensitive fields and datetime objects)
        safe_user = {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'address': user.get('address'),
            'pin_code': user.get('pin_code'),
            'vehicle_number': user.get('vehicle_number')
        }
        store_token(token, safe_user, 3600)  # 1 hour TTL
        
        return jsonify({
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'role': user['role']
            },
            'access_token': token,
            'refresh_token': token,
            'token_type': 'bearer'
        })
        
    finally:
        cursor.close()
        conn.close()

# ============================================
# USER ROUTES
# ============================================

@app.route('/api/users/me', methods=['GET'])
@require_auth
def get_profile():
    """Get current user profile"""
    user = request.user
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Get full user data from database
        cursor.execute("SELECT * FROM users WHERE id = %s", (user['id'],))
        db_user = cursor.fetchone()
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get stats
        cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE user_id = %s", (user['id'],))
        total_bookings = cursor.fetchone()['total']
        
        # Get user vehicles (extract from vehicle_number field if stored)
        vehicles = []
        if db_user.get('vehicle_number'):
            # For now, return the primary vehicle number
            vehicles = [{'vehicle_number': db_user['vehicle_number'], 'primary': True}]
        
        return jsonify({
            'id': db_user['id'],
            'name': db_user['name'],
            'email': db_user['email'],
            'address': db_user['address'],
            'pin_code': db_user['pin_code'],
            'vehicle_number': db_user['vehicle_number'],
            'vehicles': vehicles,
            'wallet_balance': float(db_user.get('wallet_balance', 0)),
            'role': db_user['role'],
            'stats': {
                'total_bookings': total_bookings,
                'total_hours_parked': 0,
                'total_amount_spent': 0,
                'most_visited_lots': []
            }
        })
    finally:
        cursor.close()
        conn.close()

# ============================================
# VEHICLE MANAGEMENT ROUTES
# ============================================

@app.route('/api/vehicles', methods=['GET'])
@require_auth
def get_vehicles():
    """Get user's vehicles"""
    user = request.user
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Get primary vehicle from user table
        cursor.execute("SELECT vehicle_number FROM users WHERE id = %s", (user['id'],))
        result = cursor.fetchone()
        
        vehicles = []
        if result and result['vehicle_number']:
            vehicles.append({
                'vehicle_number': result['vehicle_number'],
                'primary': True
            })
        
        return jsonify(vehicles)
    finally:
        cursor.close()
        conn.close()

@app.route('/api/vehicles/<vehicle_number>', methods=['PUT'])
@require_auth
def update_vehicle(vehicle_number):
    """Update user's primary vehicle"""
    user = request.user
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Update primary vehicle
        cursor.execute("""
            UPDATE users SET vehicle_number = %s, updated_at = NOW()
            WHERE id = %s
        """, (data.get('vehicle_number', vehicle_number), user['id']))
        
        conn.commit()
        
        return jsonify({
            'vehicle_number': data.get('vehicle_number', vehicle_number),
            'primary': True
        })
    finally:
        cursor.close()
        conn.close()

@app.route('/api/vehicles', methods=['POST'])
@require_auth
def add_vehicle():
    """Add a new vehicle for user"""
    user = request.user
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        vehicle_number = data.get('vehicle_number', '').strip()
        if not vehicle_number or len(vehicle_number) < 3:
            return jsonify({'error': 'Invalid vehicle number'}), 400
        
        # Update user's vehicle number (for now, just primary vehicle)
        cursor.execute("""
            UPDATE users SET vehicle_number = %s, updated_at = NOW()
            WHERE id = %s
        """, (vehicle_number, user['id']))
        
        conn.commit()
        
        return jsonify({
            'vehicle_number': vehicle_number,
            'primary': True
        }), 201
    finally:
        cursor.close()
        conn.close()

# ============================================
# PARKING ROUTES
# ============================================

@app.route('/api/parking/search', methods=['GET'])
def search_parking():
    """Search for parking lots with dynamic pricing"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        query = request.args.get('q', '')
        pin_code = request.args.get('pin_code', '')
        
        sql = "SELECT * FROM parking_lots WHERE is_active = true"
        params = []
        
        if query:
            sql += " AND (name LIKE %s OR city LIKE %s)"
            params.extend([f'%{query}%', f'%{query}%'])
        
        if pin_code:
            sql += " AND pin_code = %s"
            params.append(pin_code)
        
        cursor.execute(sql, params)
        lots = cursor.fetchall()
        
        # Get availability for each lot and calculate dynamic pricing
        for lot in lots:
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM parking_spots 
                WHERE lot_id = %s 
                GROUP BY status
            """, (lot['id'],))
            
            counts = {row['status']: row['count'] for row in cursor.fetchall()}
            available = counts.get('AVAILABLE', 0)
            occupied = counts.get('OCCUPIED', 0)
            reserved = counts.get('RESERVED', 0)
            
            lot['available_spots'] = available
            lot['occupied_spots'] = occupied
            lot['reserved_spots'] = reserved
            
            # Dynamic pricing based on occupancy and time
            total = lot['total_spots']
            if total > 0:
                occupancy_rate = (occupied + reserved) / total
                
                # Base multiplier from occupancy
                if occupancy_rate >= 0.95:
                    occupancy_multiplier = 2.0
                elif occupancy_rate >= 0.85:
                    occupancy_multiplier = 1.8
                elif occupancy_rate >= 0.70:
                    occupancy_multiplier = 1.5
                elif occupancy_rate >= 0.50:
                    occupancy_multiplier = 1.2
                else:
                    occupancy_multiplier = 1.0
                
                # Time-based multiplier
                current_hour = datetime.now().hour
                if (9 <= current_hour <= 11) or (17 <= current_hour <= 20):  # Peak hours
                    time_multiplier = 1.3
                elif 12 <= current_hour <= 16:  # Afternoon
                    time_multiplier = 1.1
                else:  # Off-peak
                    time_multiplier = 0.9
                
                # Combine multipliers
                final_multiplier = occupancy_multiplier * time_multiplier
                
                lot['base_rate'] = float(lot['hourly_rate'])
                lot['dynamic_rate'] = round(float(lot['hourly_rate']) * final_multiplier, 2)
                lot['price_multiplier'] = round(final_multiplier, 2)
                lot['occupancy_percent'] = round(occupancy_rate * 100, 1)
                lot['time_multiplier'] = time_multiplier
                lot['is_peak_hour'] = time_multiplier > 1.0
            else:
                lot['base_rate'] = float(lot['hourly_rate'])
                lot['dynamic_rate'] = float(lot['hourly_rate'])
                lot['price_multiplier'] = 1.0
                lot['occupancy_percent'] = 0
        
        return jsonify(lots)
        
    finally:
        cursor.close()
        conn.close()

@app.route('/api/parking/lots/<int:lot_id>/spots', methods=['GET'])
def get_lot_spots(lot_id):
    """Get parking spots for a lot"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("SELECT * FROM parking_spots WHERE lot_id = %s", (lot_id,))
        spots = cursor.fetchall()
        return jsonify(spots)
    finally:
        cursor.close()
        conn.close()

# ============================================
# BOOKING ROUTES
# ============================================

@app.route('/api/bookings', methods=['POST'])
@require_auth
def create_booking():
    """Create a new booking"""
    data = request.json
    user = request.user
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Validate required fields
        if not data.get('lot_id'):
            return jsonify({'error': 'Lot ID is required'}), 400
        
        if not data.get('vehicle_number'):
            return jsonify({'error': 'Vehicle number is required'}), 400
        
        # Validate payment method (only UPI and Card allowed, no cash)
        payment_method = data.get('payment_method', 'upi')
        if payment_method not in ['upi', 'card', 'wallet']:
            return jsonify({'error': 'Invalid payment method. Only UPI, Card, and Wallet are supported'}), 400
        
        # Get duration and hourly rate
        duration_hours = data.get('duration_hours', 1)
        hourly_rate = data.get('hourly_rate', 0)
        total_cost = duration_hours * hourly_rate
        
        # Find available spot
        if data.get('spot_id'):
            cursor.execute("""
                SELECT * FROM parking_spots 
                WHERE id = %s AND lot_id = %s AND status = 'AVAILABLE'
                FOR UPDATE
            """, (data['spot_id'], data['lot_id']))
        else:
            cursor.execute("""
                SELECT * FROM parking_spots 
                WHERE lot_id = %s AND status = 'AVAILABLE'
                LIMIT 1 FOR UPDATE
            """, (data['lot_id'],))
        
        spot = cursor.fetchone()
        if not spot:
            return jsonify({'error': 'No available spots'}), 400
        
        vehicle_number = data.get('vehicle_number')
        
        # Create booking
        cursor.execute("""
            INSERT INTO bookings (user_id, lot_id, spot_id, vehicle_number, start_time, duration_hours, hourly_rate, total_cost, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, 'ACTIVE', NOW(), NOW())
            RETURNING id
        """, (user['id'], data['lot_id'], spot['id'], vehicle_number, duration_hours, hourly_rate, total_cost))
        
        booking_id = cursor.fetchone()['id']
        
        # Update spot status
        cursor.execute("""
            UPDATE parking_spots 
            SET status = 'OCCUPIED', current_booking_id = %s 
            WHERE id = %s
        """, (booking_id, spot['id']))
        
        conn.commit()
        
        # Get booking with lot details
        cursor.execute("""
            SELECT b.*, l.name as lot_name, l.hourly_rate as lot_hourly_rate, ps.spot_code
            FROM bookings b
            JOIN parking_lots l ON b.lot_id = l.id
            JOIN parking_spots ps ON b.spot_id = ps.id
            WHERE b.id = %s
        """, (booking_id,))
        booking = cursor.fetchone()
        
        total_cost = booking['total_cost'] if booking['total_cost'] else (booking['duration_hours'] * booking['hourly_rate'])
        
        return jsonify({
            'id': booking['id'],
            'user_id': booking['user_id'],
            'lot_id': booking['lot_id'],
            'lot_name': booking['lot_name'],
            'spot_id': booking['spot_id'],
            'spot_code': booking['spot_code'],
            'vehicle_number': booking['vehicle_number'],
            'start_time': booking['start_time'].isoformat() if booking['start_time'] else None,
            'duration_hours': booking['duration_hours'],
            'hourly_rate': booking['hourly_rate'],
            'total_cost': float(total_cost),
            'status': booking['status']
        }), 201
        
    finally:
        cursor.close()
        conn.close()

@app.route('/api/bookings/<int:booking_id>/release', methods=['POST'])
@require_auth
def release_booking(booking_id):
    """Release (end) a booking"""
    user = request.user
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Get booking
        cursor.execute("""
            SELECT b.*, l.hourly_rate 
            FROM bookings b
            JOIN parking_lots l ON b.lot_id = l.id
            WHERE b.id = %s AND b.user_id = %s AND b.status = 'ACTIVE'
        """, (booking_id, user['id']))
        
        booking = cursor.fetchone()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Calculate cost
        start_time = booking['start_time']
        end_time = datetime.now()
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        hours = duration_minutes / 60
        total_cost = float(booking['hourly_rate']) * hours
        
        # Update booking
        cursor.execute("""
            UPDATE bookings 
            SET end_time = NOW(), duration_minutes = %s, total_cost = %s, status = 'COMPLETED', updated_at = NOW()
            WHERE id = %s
        """, (duration_minutes, total_cost, booking_id))
        
        # Update spot
        cursor.execute("""
            UPDATE parking_spots 
            SET status = 'AVAILABLE', current_booking_id = NULL 
            WHERE id = %s
        """, (booking['spot_id'],))
        
        conn.commit()
        
        # Get updated booking
        cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        updated_booking = cursor.fetchone()
        
        return jsonify(updated_booking)
        
    finally:
        cursor.close()
        conn.close()

@app.route('/api/bookings', methods=['GET'])
@require_auth
def get_bookings():
    """Get user bookings"""
    user = request.user
    status = request.args.get('status', 'ALL')
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        sql = "SELECT * FROM bookings WHERE user_id = %s"
        params = [user['id']]
        
        if status != 'ALL':
            sql += " AND status = %s"
            params.append(status)
        
        sql += " ORDER BY created_at DESC"
        
        cursor.execute(sql, params)
        bookings = cursor.fetchall()
        
        # Convert datetimes to ISO format for JSON serialization
        for booking in bookings:
            for key, value in booking.items():
                if isinstance(value, datetime):
                    booking[key] = value.isoformat()
        
        return jsonify(bookings)
        
    finally:
        cursor.close()
        conn.close()

@app.route('/api/bookings/<int:booking_id>', methods=['GET'])
@require_auth
def get_booking_details(booking_id):
    """Get single booking details for confirmation page"""
    user = request.user
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT b.*, l.name as lot_name, ps.spot_code
            FROM bookings b
            JOIN parking_lots l ON b.lot_id = l.id
            JOIN parking_spots ps ON b.spot_id = ps.id
            WHERE b.id = %s AND b.user_id = %s
        """, (booking_id, user['id']))
        
        booking = cursor.fetchone()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Convert datetime to ISO format
        total_cost = booking['total_cost'] if booking['total_cost'] else (booking['duration_hours'] * booking['hourly_rate'] if booking['duration_hours'] and booking['hourly_rate'] else 0)
        return jsonify({
            'id': booking['id'],
            'lot_id': booking['lot_id'],
            'lot_name': booking['lot_name'],
            'spot_id': booking['spot_id'],
            'spot_code': booking['spot_code'],
            'vehicle_number': booking['vehicle_number'],
            'start_time': booking['start_time'].isoformat() if booking['start_time'] else None,
            'duration_hours': booking['duration_hours'],
            'hourly_rate': booking['hourly_rate'],
            'total_cost': float(total_cost),
            'status': booking['status']
        })
        
    finally:
        cursor.close()
        conn.close()

# ============================================
# ADMIN ROUTES
# ============================================

@app.route('/api/admin/parking-lots', methods=['POST'])
@require_admin
def create_parking_lot():
    """Create a new parking lot (Admin only)"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Create lot
        cursor.execute("""
            INSERT INTO parking_lots (name, address, city, pin_code, latitude, longitude, total_spots, hourly_rate, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (
            data['name'], data['address'], data['city'], data['pin_code'],
            data.get('latitude'), data.get('longitude'),
            data['total_spots'], data['hourly_rate']
        ))
        
        lot_id = cursor.lastrowid
        
        # Create spots
        for i in range(1, data['total_spots'] + 1):
            section = chr(65 + (i - 1) // 50)
            number = (i - 1) % 50 + 1
            spot_code = f"{section}-{number:02d}"
            
            cursor.execute("""
                INSERT INTO parking_spots (lot_id, spot_code, status, created_at, updated_at)
                VALUES (%s, %s, 'AVAILABLE', NOW(), NOW())
            """, (lot_id, spot_code))
        
        conn.commit()
        
        # Get created lot
        cursor.execute("SELECT * FROM parking_lots WHERE id = %s", (lot_id,))
        lot = cursor.fetchone()
        
        return jsonify(lot), 201
        
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/parking-lots/<int:lot_id>', methods=['PUT'])
@require_admin
def update_parking_lot(lot_id):
    """Update a parking lot (Admin only)"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Check if lot exists
        cursor.execute("SELECT id FROM parking_lots WHERE id = %s", (lot_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Parking lot not found'}), 404
        
        # Update lot
        cursor.execute("""
            UPDATE parking_lots 
            SET name = %s, address = %s, city = %s, pin_code = %s, hourly_rate = %s, updated_at = NOW()
            WHERE id = %s
        """, (
            data['name'], data['address'], data['city'], 
            data['pin_code'], data['hourly_rate'], lot_id
        ))
        
        conn.commit()
        
        # Get updated lot
        cursor.execute("SELECT * FROM parking_lots WHERE id = %s", (lot_id,))
        lot = cursor.fetchone()
        
        return jsonify(lot)
        
    finally:
        cursor.close()
        conn.close()

@app.route('/api/admin/analytics/overview', methods=['GET'])
@require_admin
def get_analytics_overview():
    """Get admin analytics overview"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Total bookings
        cursor.execute("SELECT COUNT(*) as total FROM bookings")
        total_bookings = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM bookings WHERE DATE(created_at) = CURDATE()")
        today_bookings = cursor.fetchone()['total']
        
        # Total revenue
        cursor.execute("SELECT COALESCE(SUM(total_cost), 0) as total FROM bookings WHERE status = 'COMPLETED'")
        total_revenue = float(cursor.fetchone()['total'])
        
        cursor.execute("SELECT COALESCE(SUM(total_cost), 0) as total FROM bookings WHERE status = 'COMPLETED' AND DATE(created_at) = CURDATE()")
        today_revenue = float(cursor.fetchone()['total'])
        
        # Occupancy
        cursor.execute("SELECT COUNT(*) as total FROM parking_spots")
        total_spots = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM parking_spots WHERE status = 'OCCUPIED'")
        occupied_spots = cursor.fetchone()['total']
        
        occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0
        
        return jsonify({
            'total_bookings': {'all_time': total_bookings, 'today': today_bookings},
            'total_revenue': {'all_time': total_revenue, 'today': today_revenue},
            'occupancy_rate': {'current': round(occupancy_rate, 2), 'by_lot': []},
            'active_users': 0
        })
        
    finally:
        cursor.close()
        conn.close()

# ============================================
# STATIC FILE SERVING (FRONTEND)
# ============================================

@app.route('/', methods=['GET'])
def root():
    """Serve frontend index.html"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>', methods=['GET'])
def serve_static(filename):
    """Serve static files from frontend directory"""
    file_path = FRONTEND_DIR / filename
    print(f"Serving static: {filename}, path: {file_path}, exists: {file_path.exists()}")
    if file_path.exists() and file_path.is_file():
        return send_from_directory(FRONTEND_DIR, filename)
    # If file doesn't exist and doesn't look like an API call, serve index.html
    if not filename.startswith('api/'):
        print(f"File not found, serving index.html for {filename}")
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return jsonify({'error': 'Not found'}), 404

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'frontend': str(FRONTEND_DIR)})

# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    print("🚀 Starting ParkHub Unified Server...")
    print("📍 Server running at http://localhost:8000")
    print("🌐 Frontend: http://localhost:8000")
    print("📚 API: http://localhost:8000/api/*")
    print(f"📁 Serving frontend from: {FRONTEND_DIR}")
    print("\n📝 Demo Credentials:")
    print("   Admin: admin@parkhub.com / admin123456")
    print("   User:  user1@parkhub.com / password123")
    app.run(host='0.0.0.0', port=8000, debug=True)
