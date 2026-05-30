import urllib.request
try:
    req = urllib.request.Request("http://localhost:8000/api/bookings?status=COMPLETED", headers={"Authorization": "Bearer TEST"})
    urllib.request.urlopen(req)
except Exception as e:
    print(e)
