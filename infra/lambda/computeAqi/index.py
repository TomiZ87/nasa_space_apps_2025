def handler(event, context):
    input_data = event

    stations_data = []
    poi = None
    hrs_values = []

    for key, value in input_data.items():
        if key == "POI_coordinate":
            lat = value.get("lat")
            lon = value.get("lon")
            if lat is not None and lon is not None:
                poi = {"lat": lat, "long": lon}
        else:
            location = value.get("location", {})
            lat = location.get("latitude")
            lon = location.get("longitude")
            aqi = value.get("AQI")
            pm25 = value.get("pm2.5")

            hrs_per_cig = None
            if pm25 is not None and pm25 > 0:
                cigs_per_day = pm25 / 22
                if cigs_per_day > 0:
                    hrs_per_cig = 24 / cigs_per_day
            elif aqi is not None and aqi > 0:  # Exclude AQI == 0
                pm25_est = (aqi / 100) * 35
                cigs_per_day = pm25_est / 22
                if cigs_per_day > 0:
                    hrs_per_cig = 24 / cigs_per_day

            # Save for averaging only if hrs_per_cig was calculated
            if hrs_per_cig is not None:
                hrs_values.append(hrs_per_cig)

            if lat is not None and lon is not None:
                stations_data.append({
                    "lat": lat,
                    "long": lon,
                    "AQI": aqi
                })

    # Calculate average hrsPerCig across all stations
    poi_hrs_per_cig = None
    if hrs_values:
        poi_hrs_per_cig = round(sum(hrs_values) / len(hrs_values), 1)  # Round to 1 decimal

    res = {
        "poi": poi,
        "hrsPerCig": poi_hrs_per_cig,
        "stationsData": stations_data
    }

    print(res)
    return res
