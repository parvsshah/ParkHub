#!/usr/bin/env python3
"""Quick API test to verify endpoints work"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

# Test 1: Login
print("\n🔐 Test 1: Login")
response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "user1@parkhub.com",
    "password": "password123"
})
print(f"Status: {response.status_code}")
data = response.json()
token = data.get('access_token')
print(f"Token: {token[:20]}...")

# Test 2: Get profile 
print("\n👤 Test 2: Get Profile")
response = requests.get(f"{BASE_URL}/users/me", headers={
    "Authorization": f"Bearer {token}"
})
print(f"Status: {response.status_code}")
profile = response.json()
print(f"User: {profile.get('name')}")
print(f"Wallet Balance: ₹{profile.get('wallet_balance')}")
print(f"Vehicles: {profile.get('vehicles')}")

# Test 3: Search parking
print("\n🅿️ Test 3: Search Parking")
response = requests.get(f"{BASE_URL}/parking/search")
print(f"Status: {response.status_code}")
lots = response.json()
print(f"Found {len(lots)} parking lots")
if lots:
    first_lot = lots[0]
    print(f"First lot: {first_lot.get('name')}")
    print(f"Available: {first_lot.get('available_spots')}")
    print(f"Rate: ₹{first_lot.get('dynamic_rate')}/hr")
    
    # Test 4: Create booking
    if first_lot.get('available_spots', 0) > 0:
        print(f"\n📍 Test 4: Create Booking")
        response = requests.post(f"{BASE_URL}/bookings", 
            headers={"Authorization": f"Bearer {token}"},
            json={
                "lot_id": first_lot['id'],
                "vehicle_number": "KA01AB1234",
                "payment_method": "upi",
                "duration_hours": 2,
                "hourly_rate": first_lot.get('dynamic_rate', 50)
            }
        )
        print(f"Status: {response.status_code}")
        booking = response.json()
        if response.status_code == 201:
            booking_id = booking.get('id')
            print(f"Booking ID: {booking_id}")
            print(f"Duration: {booking.get('duration_hours')}h")
            print(f"Total Cost: ₹{booking.get('total_cost')}")
            
            # Test 5: Get booking details
            print(f"\n📋 Test 5: Get Booking Details")
            response = requests.get(f"{BASE_URL}/bookings/{booking_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                booking_details = response.json()
                print(f"Booking confirmed:")
                print(f"  Lot: {booking_details.get('lot_name')}")
                print(f"  Spot: {booking_details.get('spot_code')}")
                print(f"  Vehicle: {booking_details.get('vehicle_number')}")
                print(f"  Duration: {booking_details.get('duration_hours')}h")
                print(f"  Cost: ₹{booking_details.get('total_cost')}")
        else:
            print(f"Error: {booking.get('error')}")
else:
    print("⚠️ No parking lots available")

print("\n✅ All tests completed!")
