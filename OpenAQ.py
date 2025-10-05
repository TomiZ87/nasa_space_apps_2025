import requests
import os
from dotenv import load_dotenv


# Get a list of nearby locations (weather stations)
def get_nearby_locations(lat: float, lon: float, api_key: str, radius: int = 10000, limit: int = 5):
    url = "https://api.openaq.org/v3/locations"
    params = {
        "coordinates": f"{lat},{lon}",
        "radius": radius,
        "limit": limit
    }
    headers = {
        "X-API-Key": api_key
    }
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    locations = resp.json().get("results", None) # The list of nearby locations
    return locations


# Query the lastest data from a location
def get_latest_data(location_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
    headers = {
        "X-API-Key": api_key
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("results", [])

# Query data from a specific sensor
def get_sensor_data(sensor_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}"
    headers = {
        "X-API-Key": api_key
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json().get("results", None)

    if results != None:
        request = results[0]
        sensor_id = request.get("id", None)
        pollutant =  request.get("parameter", None)
        sensor_data = request.get("latest", None)
        if sensor_data != None:
            time = sensor_data.get("datetime", None)
            value = sensor_data.get("value", None)
            location = sensor_data.get("coordinates", None)

    category = {
        "sensor_id": sensor_id,
        "pollutant_info": pollutant,
        "time": time,
        "value": value,
        "location": location
    }

    return category


def get_air_quality(lat: float, lon: float, api_key: str):
    locations = get_nearby_locations(lat, lon, api_key)

    if locations == None:
        print("No nearby monitoring stations found.")
        return

    for loc in locations:
        loc_id = loc["id"]
        loc_name = loc.get("name", "Unnamed")
        print(f"Station {loc_id}: {loc_name}")
        try:
            latest = get_latest_data(loc_id, api_key)
            for entry in latest:
                sensors_id = entry.get("sensorsId", []) # Get the sensor id to request the data from a specific sensor
                value = entry.get("value", None) # Get the value of a specific sensor from the request "latest_data"

                sensor_data = get_sensor_data(sensors_id, api_key)
                # for sanity check - check if the sensors_id and the data value in lastest request match with sensors request
                if value == sensor_data["value"]:
                    print("This is the hourly updated real-time data:", sensor_data)

        except requests.HTTPError as e:
            print(f"  Could not fetch latest for location {loc_id}: {e}")
        print()


def main():
    load_dotenv()  # loads .env into environment
    YOUR_API_KEY = os.getenv("OPENAQ_KEY")
    lat, lon = 37.7749, -122.4194
    get_air_quality(lat, lon, YOUR_API_KEY)

if __name__ == "__main__":
    main()
