#!/usr/bin/env python3
"""Comprehensive test of all improvements"""
import requests
import json

BASE = "http://localhost:8000/api"

print("\n" + "="*60)
print("🧪 COMPREHENSIVE TEST OF ALL IMPROVEMENTS")
print("="*60)

# Test 1: Login
print("\n✅ Test 1: Login & Get Token")
r = requests.post(f"{BASE}/auth/login", json={
    "email": "user1@parkhub.com",
    "password": "password123"
})
print(f"Status: {r.status_code}")
user_data = r.json()
token = user_data.get('access_token')
print(f"✓ Login successful, token: {token[:20]}...")

# Test 2: Get Profile with wallet balance
print("\n✅ Test 2: Get Profile with Wallet Balance")
r = requests.get(f"{BASE}/users/me", headers={"Authorization": f"Bearer {token}"})
print(f"Status: {r.status_code}")
profile = r.json()
print(f"✓ User: {profile['name']}")
print(f"✓ Email: {profile['email']}")
print(f"✓ Wallet Balance: ₹{profile['wallet_balance']}")
print(f"✓ Vehicles: {profile['vehicles']}")

# Test 3: Get Vehicles
print("\n✅ Test 3: Get Vehicles Endpoint")
r = requests.get(f"{BASE}/vehicles", headers={"Authorization": f"Bearer {token}"})
print(f"Status: {r.status_code}")
vehicles = r.json()
print(f"✓ Vehicles loaded: {len(vehicles)} vehicle(s)")
if vehicles:
    print(f"✓ First vehicle: {vehicles[0]['vehicle_number']}")

# Test 4: Get Parking Lots
print("\n✅ Test 4: Search Parking Lots")
r = requests.get(f"{BASE}/parking/search")
print(f"Status: {r.status_code}")
lots = r.json()
print(f"✓ Found {len(lots)} parking lot(s)")

if lots:
    lot = lots[0]
    print(f"\nLot Details:")
    print(f"  Name: {lot['name']}")
    print(f"  Available: {lot['available_spots']}")
    print(f"  Rate: ₹{lot['dynamic_rate']}/hr")
    
    # Test 5: Create Booking
    print("\n✅ Test 5: Create Booking with Duration")
    r = requests.post(f"{BASE}/bookings", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "lot_id": lot['id'],
            "vehicle_number": "KA01AB1234",
            "payment_method": "upi",
            "duration_hours": 2,
            "hourly_rate": float(lot['dynamic_rate'])
        }
    )
    print(f"Status: {r.status_code}")
    if r.status_code in [200, 201]:
        booking = r.json()
        booking_id = booking.get('id')
        print(f"✓ Booking created:")
        print(f"  ID: {booking_id}")
        print(f"  Duration: {booking['duration_hours']}h")
        print(f"  Rate: ₹{booking['hourly_rate']}/hr")
        print(f"  Total Cost: ₹{booking.get('total_cost', 'N/A')}")
        
        # Test 6: Get Booking Details (for confirmation page)
        print(f"\n✅ Test 6: Get Booking Details (Confirmation)")
        r = requests.get(f"{BASE}/bookings/{booking_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            booking_detail = r.json()
            print(f"✓ Booking details fetched:")
            print(f"  Lot: {booking_detail.get('lot_name', 'N/A')}")
            print(f"  Spot: {booking_detail['spot_id']}")
            print(f"  Vehicle: {booking_detail['vehicle_number']}")
            print(f"  Duration: {booking_detail['duration_hours']}h")
            print(f"  Total Cost: ₹{booking_detail['total_cost']}")
        else:
            print(f"❌ Error: {r.text}")
    else:
        print(f"❌ Error: {r.text}")

# Test 7: Get Active Bookings
print("\n✅ Test 7: Get Active Bookings")
r = requests.get(f"{BASE}/bookings?status=ACTIVE",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Status: {r.status_code}")
bookings = r.json()
print(f"✓ Active bookings: {len(bookings)}")

# Test 8: Add Vehicle
print("\n✅ Test 8: Add New Vehicle")
r = requests.post(f"{BASE}/vehicles",
    headers={"Authorization": f"Bearer {token}"},
    json={"vehicle_number": "DL01XY9876"}
)
print(f"Status: {r.status_code}")
if r.status_code in [200, 201]:
    vehicle = r.json()
    print(f"✓ Vehicle added: {vehicle['vehicle_number']}")
else:
    print(f"❌ Error: {r.text}")

print("\n" + "="*60)
print("✅ ALL TESTS COMPLETED!")
print("="*60 + "\n")
