import requests
from datetime import datetime, timedelta
import json
import os
import sys

def fetch_tomorrow_spot_prices(mock=False):
    if mock:
        file_path = "output/20250225.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        else:
            print(f"Mock file {file_path} not found.")
            return None

    
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime("%Y/%m-%d")
    region = "SE4"

    url = f"https://www.elprisetjustnu.se/api/v1/prices/{date_str}_{region}.json"


    try:
        response = requests.get(url, timeout=5)  # Set a timeout for the request
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def print_json(data):
    if data is not None:
        print(json.dumps(data, indent=2))
    else:
        print("No data to display")

if __name__ == "__main__":
    mock=True
    spot_prices = fetch_tomorrow_spot_prices(mock)
    print_json(spot_prices);
    print("===========\nMock output", file=sys.stderr)

