import requests
import json
from datetime import datetime

# limit: 10 calls/minute and 5000/month
api_token = None
app_id = '13de259b'
api_url = 'https://api.traveltimeapp.com/v4/time-map'

pointCoords = [13.673966, 51.091271]

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Application-Id': app_id,
    'X-Api-Key': api_token}

# up to 10 searches per request
data = {
    "departure_searches": [
        {
            "id": "example stop",
            "coords": {
                "lng": pointCoords[0],
                "lat": pointCoords[1]
            },
            "transportation": {
                "type": "walking"
            },
            "travel_time": 300,
            "departure_time": datetime.now().isoformat()
        }
    ]
}

response = requests.post(api_url, headers=headers,  json=data)

print(response.json())
