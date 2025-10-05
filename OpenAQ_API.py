import requests

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
    print("all nearby loc:", resp.json())
    resp.raise_for_status()
    return resp.json().get("results", [])

def get_location_latest(location_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
    headers = {
        "X-API-Key": api_key
    }
    resp = requests.get(url, headers=headers)
    print(resp.json())
    resp.raise_for_status()
    return resp.json().get("results", [])

def get_air_quality(lat: float, lon: float, api_key: str):
    locations = get_nearby_locations(lat, lon, api_key)
    if not locations:
        print("No nearby monitoring stations found.")
        return

    for loc in locations:
        loc_id = loc["id"]
        loc_name = loc.get("name", "Unnamed")
        print(f"Station {loc_id}: {loc_name}")
        try:
            latest = get_location_latest(loc_id, api_key)
            for entry in latest:
                measurements = entry.get("measurements", [])
                for m in measurements:
                    print(m)
                    print(f"  - {m['parameter']} = {m['value']} {m['unit']} (time: {m['date']['utc']})")
        except requests.HTTPError as e:
            print(f"  Could not fetch latest for location {loc_id}: {e}")
        print()

if __name__ == "__main__":
    YOUR_API_KEY = "e5f33bf244d39184d6c7b4ff83c9f0ea5b5d444441dad51ffe33ed3d6025dc24"
    lat, lon = 37.7749, -122.4194
    get_air_quality(lat, lon, YOUR_API_KEY)
