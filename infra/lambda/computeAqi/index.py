import os
import boto3
import json
from datetime import datetime, timezone
from decimal import Decimal
import uuid

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['TABLE_NAME']
table = dynamodb.Table(table_name)

# Helper to convert floats to Decimal for DynamoDB
def to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_decimal(i) for i in obj]
    else:
        return obj

def handler(event, context):
    # If the event has a body (e.g., from another Lambda HTTP response), parse it
    if "body" in event:
        input_data = json.loads(event["body"])
    else:
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
                poi_id = f"{lat},{lon}"  # Use lat,long as POI ID
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

            if hrs_per_cig is not None:
                hrs_values.append(hrs_per_cig)

            if lat is not None and lon is not None:
                stations_data.append({
                    "lat": lat,
                    "long": lon,
                    "AQI": aqi
                })

    poi_hrs_per_cig = None
    if hrs_values:
        poi_hrs_per_cig = round(sum(hrs_values) / len(hrs_values), 1)

    res = {
        "poi": poi,
        "hrsPerCig": poi_hrs_per_cig,
        "stationsData": stations_data
    }

    # Insert into DynamoDB
    if poi_hrs_per_cig is not None and poi is not None:
        now = datetime.now(timezone.utc)
        table.put_item(Item=to_decimal({
            "poiId": poi_id,              # Partition key
            "timestamp": now.isoformat(), # Sort key
            "id": str(uuid.uuid4()),      # Unique UUID
            "poi": poi,
            "hrsPerCig": poi_hrs_per_cig,
            "stationsData": stations_data
        }))

    print(res)
    return res
