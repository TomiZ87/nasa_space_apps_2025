import requests
import os
from dotenv import load_dotenv

# Get a list of nearby stations (weather stations)
def get_nearby_stations(lat: float, lon: float, api_key: str, radius: int = 10000, limit: int = 5):
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


# Query the lastest data from a station (location)
def get_latest_data(station_id: int, api_key: str):
    url = f"https://api.openaq.org/v3/locations/{station_id}/latest"
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


# Function to calculate the AQI for one pollutant
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
                
                # Return the final index
                return int(round(I))
    else:
        return None


def get_air_quality(lat: float, lon: float, api_key: str):
    
    # Get all of the stations in the area
    stations = get_nearby_stations(lat, lon, api_key)

    # Dictionary of stations with their info (Lat, lon, AQI, PM25)
    stations_dictionary = {}

    # Handle cases where there are no stations around
    if stations == None:
        print("No nearby monitoring stations found.")
        return

    # Iterate through the stations
    print("Iterating through the stations")

    for station in stations:
        
        # Save station data for future use
        station_id = station["id"]
        station_AQI = 0
        stations_dictionary[station_id]={}

        # Get the latest data for the station
        latest = get_latest_data(station_id, api_key)

        # Iterate through sensors
        print("Iterating through the sensors")

        for sensor in latest:
            sensors_id = sensor.get("sensorsId", [])                # Get the sensor id to request the data from a specific sensor
            latest_value = sensor.get("value", None)                # Get the value of a specific sensor from the request "latest_data"

            sensor_data = get_sensor_data(sensors_id, api_key)      # Get the sensor data through another path
            sensor_value = sensor_data["value"]                     # Get the sensor value 

            station = stations_dictionary[station_id]               # Get the current station in the dictionary
            station.update({'location': sensor_data["location"]})   # Add the station location to the dictionary

            # Sanity check - check if the sensors_id and the data value in lastest request match with sensors request
            if sensor_data != None and latest_value == sensor_value:

                # Fixing the pollutant concentration level (i.e., changing from ppm to ppb )
                if sensor_data["pollutant_info"]["units"] == "ppm":
                    sensor_value = sensor_value * 1000

                # Find pm2.5 poluttants and save their values for future cigarette calculation
                if sensor_data["pollutant_info"]["name"] == "pm25":
                    station.update({'pm2.5': sensor_value})

                print("Calculating the AQI")
                currentAQI = calculateAQI(sensor_value, sensor_data["pollutant_info"]["name"])

                # Logic to find the highest AQI for the station
                if currentAQI != None and currentAQI > station_AQI:
                    station_AQI = currentAQI

            # Update the station dictionary and add the AQI info    
            station.update({'AQI': station_AQI})  

    # Return all of the collected data from the station
    return stations_dictionary


def main():
    load_dotenv()                                           # loads .env into environment
    YOUR_API_KEY = os.getenv("OPENAQ_KEY")                  # Save the api key
    lat, lon = 37.7749, -122.4194                           # Define lat and lon (TODO: change so it's not hard coded)
    dictionary = get_air_quality(lat, lon, YOUR_API_KEY)    # Retrieve all data for the POI (point of interest)
    dictionary["POI_coordinate"] = {"lat": lat, "lon": lon} # Add the POI to the collected data

    print(dictionary)

if __name__ == "__main__":
    main()
