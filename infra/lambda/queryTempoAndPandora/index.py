import os
import urllib.request
import json

# --- Helper Functions ---

def fetch_json(url, headers=None, params=None):
    """Fetch JSON from a URL using urllib, with optional headers and query params."""
    if params:
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query_string}"
    req = urllib.request.Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())

def get_nearby_stations(lat: float, lon: float, api_key: str, radius: int = 10000, limit: int = 5):
    url = "https://api.openaq.org/v3/locations"
    params = {
        "coordinates": f"{lat},{lon}",
        "radius": radius,
        "limit": limit
    }
    headers = {"X-API-Key": api_key}
    return fetch_json(url, headers, params).get("results", [])

def get_latest_data(station_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/locations/{station_id}/latest"
    headers = {"X-API-Key": api_key}
    return fetch_json(url, headers).get("results", [])

def get_sensor_data(sensor_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}"
    headers = {"X-API-Key": api_key}
    results = fetch_json(url, headers).get("results", [])
    if not results:
        return None

    request = results[0]
    sensor_data = request.get("latest", {})
    return {
        "sensor_id": request.get("id"),
        "pollutant_info": request.get("parameter"),
        "time": sensor_data.get("datetime"),
        "value": sensor_data.get("value"),
        "location": sensor_data.get("coordinates"),
    }

def calculateAQI(concentration, pollutant):
    BREAKPOINTS = {
        "pm25": [
            (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150), (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400),
            (350.5, 500.4, 401, 500)
        ]
    }
    if pollutant not in BREAKPOINTS or concentration is None:
        return None
    for C_lo, C_hi, I_lo, I_hi in BREAKPOINTS[pollutant]:
        if C_lo <= concentration <= C_hi:
            I = (I_hi - I_lo) / (C_hi - C_lo) * (concentration - C_lo) + I_lo
            return int(round(I))
    return None

# --- Lambda Handler ---

def handler(event, context):
    # Hardcoded POI (New Delhi)
    lat, lon = 28.61, 77.23
    api_key = os.environ.get("OPENAQ_KEY")
    if not api_key:
        return {"statusCode": 500, "body": "Missing OpenAQ API key in environment variables"}

    stations = get_nearby_stations(lat, lon, api_key)
    if not stations:
        return {"statusCode": 200, "body": json.dumps({
            "POI_coordinate": {"lat": lat, "lon": lon},
            "stations": {}
        })}

    stations_dict = {}

    for station in stations:
        station_id = station["id"]
        station_aqi = 0
        stations_dict[station_id] = {}

        latest_data = get_latest_data(station_id, api_key)

        for sensor in latest_data:
            sensors_id = sensor.get("sensorsId")
            latest_value = sensor.get("value")

            sensor_data = get_sensor_data(sensors_id, api_key)
            if not sensor_data:
                continue

            station_info = stations_dict[station_id]
            station_info["location"] = sensor_data["location"]

            if latest_value == sensor_data["value"]:
                value = sensor_data["value"]

                # Convert ppm to ppb if needed
                if sensor_data["pollutant_info"]["units"] == "ppm":
                    value *= 1000

                if sensor_data["pollutant_info"]["name"] == "pm25":
                    station_info["pm2.5"] = value

                current_aqi = calculateAQI(value, sensor_data["pollutant_info"]["name"])
                if current_aqi and current_aqi > station_aqi:
                    station_aqi = current_aqi

            station_info["AQI"] = station_aqi

    stations_dict["POI_coordinate"] = {"lat": lat, "lon": lon}

    print(stations_dict)

    return {"statusCode": 200, "body": json.dumps(stations_dict)}
