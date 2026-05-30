# 🚗 ParkHub - Smart Parking Management System

A simple parking management system built with Flask (Python) and pure HTML/CSS/JavaScript.

## 📁 Project Structure

```
ParkHub/
├── backend/           # Flask API server
│   ├── app.py         # Main application
│   ├── scripts/       # Database setup scripts
│   └── requirements.txt
└── html-version/      # Frontend (HTML/CSS/JS)
    ├── index.html     # Landing page
    ├── login.html     # User login
    ├── register.html  # User registration
    ├── dashboard.html # User dashboard
    ├── admin-login.html
    ├── admin-dashboard.html
    ├── js/            # JavaScript files
    └── styles/        # CSS files
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd backend
pip3 install -r requirements.txt
```

### 2. Setup Database
```bash
cd backend
python3 scripts/create_db.py   # Create database
python3 scripts/init_db.py     # Create tables
python3 scripts/seed.py        # Add sample data
```

Or use npm shortcut:
```bash
cd backend
npm run setup
```

### 3. Run the Server
```bash
cd backend
python3 app.py
```

Or:
```bash
cd backend
npm run dev
```

**Server runs at**: http://localhost:8000

---

## 🔑 Login Credentials

**User:**
- user1@parkhub.com / password123
- user2@parkhub.com / password123

**Admin:**
- admin@parkhub.com / admin123456

---

## ✨ Features

### User Features
- Search parking lots
- Book parking spots
- View booking history
- End/release parking sessions

### Admin Features
- View analytics dashboard
- Create parking lots
- Monitor occupancy rates

---

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Database**: MySQL
- **Frontend**: Pure HTML/CSS/JavaScript

---

## 📚 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | User login |
| POST | /api/auth/register | User registration |
| GET | /api/users/me | Get user profile |
| GET | /api/parking/search | Search parking lots |
| POST | /api/bookings | Create booking |
| GET | /api/bookings | Get user bookings |
| POST | /api/bookings/:id/release | End booking |
| GET | /api/admin/analytics/overview | Admin analytics |
| POST | /api/admin/parking-lots | Create parking lot |
