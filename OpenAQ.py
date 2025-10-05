import requests
import os
from dotenv import load_dotenv


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
    # The list of locations
    locations = resp.json().get("results", [])
    # The list of sensors from that location - for sanity check
    sensors = locations[0].get("sensors", [])
    return locations, sensors


def get_latest_data(location_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
    headers = {
        "X-API-Key": api_key
    }
    resp = requests.get(url, headers=headers)
    print(resp.json())
    resp.raise_for_status()
    return resp.json().get("results", [])

def get_pollutants(sensors_list):
    for sensor in sensors_list:
        sensor_id = sensor.get("id")
        pollutant = sensor.get("parameter", None)

        if pollutant != None:
            pollutant_id = pollutant.get("id")
            pollutant_name = pollutant.get("name")
            pollutant_units = pollutant.get("units")
            pollutant_display_name = pollutant.get("displayName")

        category = {
            "sensor_id": sensor_id,
            "pollutant_id": pollutant_id,
            "name": pollutant_name,
            "units": pollutant_units,
            "display_name": pollutant_display_name
        }

        return category


def get_sensor_data(sensor_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}"
    headers = {
        "X-API-Key": api_key
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    results = resp.json().get("results", None)
    if results != None:
        sensor_id = results[0].get("id")
        value = results[0]["latest"]["value"]
        pollutant =  results[0].get("parameter", None)
        if pollutant != None:
            pollutant_id = pollutant.get("id")
            pollutant_name = pollutant.get("name")
            pollutant_units = pollutant.get("units")
            pollutant_display_name = pollutant.get("displayName")

    category = {
        "sensor_id": sensor_id,
        "pollutant_id": pollutant_id,
        "name": pollutant_name,
        "units": pollutant_units,
        "display_name": pollutant_display_name,
        "value": value
    }

    return category


def get_air_quality(lat: float, lon: float, api_key: str):
    locations, sensors = get_nearby_locations(lat, lon, api_key)

    # for sanity check - check if the sensors is the same as the lastest data retrieval
    #pollutant = get_pollutants(sensors)

    if not locations:
        print("No nearby monitoring stations found.")
        return

    for loc in locations:
        loc_id = loc["id"]
        loc_name = loc.get("name", "Unnamed")
        print(f"Station {loc_id}: {loc_name}")
        try:
            latest = get_latest_data(loc_id, api_key)
            for entry in latest:
                sensors_id = entry.get("sensorsId", [])
                #value = entry.get("value", None)
                #if value != None:
                #    pollutant["value"] = value
                data = get_sensor_data(sensors_id, api_key)
                #if data == pollutant:
                print("This is data:", data)
                #print("This is pollutant:", pollutant)
        except requests.HTTPError as e:
            print(f"  Could not fetch latest for location {loc_id}: {e}")
        print()

if __name__ == "__main__":
    load_dotenv()  # loads .env into environment

    YOUR_API_KEY = os.getenv("OPENAQ_KEY")
    lat, lon = 37.7749, -122.4194
    get_air_quality(lat, lon, YOUR_API_KEY)
