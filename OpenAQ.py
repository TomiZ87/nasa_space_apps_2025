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


# Function to calculate the AQI for a pollutant
def calculateAQI(concentration, pollutant):
    # Dictionary of breakpoints for each pollutant
    BREAKPOINTS = {
        "pm25": [
            (0.0, 12.0, 0, 50),
            (12.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, 350.4, 301, 400),
            (350.5, 500.4, 401, 500),
        ],
        "pm10": [
            (0, 54, 0, 50),
            (55, 154, 51, 100),
            (155, 254, 101, 150),
            (255, 354, 151, 200),
            (355, 424, 201, 300),
            (425, 504, 301, 400),
            (505, 604, 401, 500),
        ],
        "no2": [
            (0, 53, 0, 50),
            (54, 100, 51, 100),
            (101, 360, 101, 150),
            (361, 649, 151, 200),
            (650, 1249, 201, 300),
            (1250, 1649, 301, 400),
            (1650, 2049, 401, 500),
        ]}

    # Check if we can use the pollutant
    if pollutant in BREAKPOINTS:
        for C_lo, C_hi, I_lo, I_hi in BREAKPOINTS[pollutant]:
            if C_lo <= concentration <= C_hi:
                # Calculate the AQI for the pollutant
                I = (I_hi - I_lo) / (C_hi - C_lo) * (concentration - C_lo) + I_lo
                return int(round(I))
    else:
        return None


def get_air_quality(lat: float, lon: float, api_key: str):
    locations = get_nearby_locations(lat, lon, api_key)

    #Dictionary of locations with their info
    locations_dic = {}

    if locations == None:
        print("No nearby monitoring stations found.")
        return

    for loc in locations:
        
        loc_id = loc["id"]
        loc_AQI = 0
        locations_dic[loc_id]={}

        loc_name = loc.get("name", "Unnamed")
        print(f"Station {loc_id}: {loc_name}")

        #Get the latest data for the station
        latest = get_latest_data(loc_id, api_key)

        #Iterate through sensors
        for sensor in latest:
            sensors_id = sensor.get("sensorsId", []) # Get the sensor id to request the data from a specific sensor
            latest_value = sensor.get("value", None) # Get the value of a specific sensor from the request "latest_data"

            sensor_data = get_sensor_data(sensors_id, api_key)
            sensor_value = sensor_data["value"]

            station = locations_dic[loc_id]
            station.update({'location': sensor_data["location"]})

            # for sanity check - check if the sensors_id and the data value in lastest request match with sensors request
            if sensor_data != None and latest_value == sensor_value:

                #Fixing the pollutant concentration level
                if sensor_data["pollutant_info"]["units"] == "ppm":
                    sensor_value = sensor_value * 1000


                if sensor_data["pollutant_info"]["name"] == "pm25":
                    station.update({'pm2.5': sensor_value})

                currentAQI = calculateAQI(sensor_value, sensor_data["pollutant_info"]["name"])
                print("This is the hourly updated real-time data:", sensor_data)
                print("This is the current AQI:", currentAQI)

                # Logic to find the highest AQI for the station
                if currentAQI != None and currentAQI > loc_AQI:
                    loc_AQI = currentAQI
                
            station.update({'AQI': loc_AQI})  


    return locations_dic


def main():
    load_dotenv() # loads .env into environment
    YOUR_API_KEY = os.getenv("OPENAQ_KEY")
    lat, lon = 37.7749, -122.4194
    dictionary = get_air_quality(lat, lon, YOUR_API_KEY) # THIS ONLY RETURNS THE LAST ONE
    dictionary["POI_coordinate"] = {"lat": lat, "lon": lon}
    
    print(dictionary)

if __name__ == "__main__":
    main()
