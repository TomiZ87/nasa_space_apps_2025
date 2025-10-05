

async function fetchData(){
    try{
        const response = await fetch("http://localhost:8080/data");
        if(!response.ok){
            throw new Error("Failed to fetch data");
        }

        const data = await response.json();
        console.log(data);

    }
    catch(error){
        console.error(error);

    }
}
function success(position){
    //doSomething(position.coords.latitude, position.coords.longitude);
    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;
    console.log(latitude, "\n", longitude);
    zoomTo(position)
}

function error(){
    alert("Sorry, no position available.");
}


function getPosition(){
    if (!navigator.geolocation) {
        status.textContent = "Geolocation is not supported by your browser";
    } else {
        status.textContent = "Locating…";
        navigator.geolocation.getCurrentPosition(success, error);
    }
}

function zoomTo(position){
    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;
    map.panTo(new L.LatLng(latitude, longitude));
}

function standardizeAQI(AQI) {
  if (AQI <= 50) {
    intensity = 0.1
  }
  else if (AQI <= 100) {
    intensity = 0.2
  }
  else if (AQI <= 150) {
    intensity = 0.3
  }
  else if (AQI <= 200) {
    intensity = 0.4
  }
  else if (AQI <= 300) {
    intensity = 0.6
  }
  else {intensity = 0.8}
  return intensity
}

function getHeatPointsArray (pointsJson) {
  var points = []
  pointsJson.data.forEach( obj => {
    var intensity = standardizeAQI(obj.AQI);
    var point = [obj.lat, obj.long, intensity];
    points.push(point)
  })
  return points
}

function getHeatMapLayer(pointsJson) {
  var points = getHeatPointsArray(pointsJson);
  var heat = L.heatLayer(points, {radius: 100})
  return heat
}

function getSanFranMap() {
  return L.map('map').setView([51.505, -0.09], 13);
}

function addCigMarkersToMap(jsonData, map) {
  jsonData.data.forEach(obj => {
    L.marker(obj.point)
      .addTo(map)
      .bindPopup(`Breathing the air in this location for ${obj.hrsPerCig} hours is the equivalent of smoking one cigarette!`)
  })
}

var map = getSanFranMap();

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap'
}).addTo(map);

var dummyCig = {"data": [
  {"point": [51.50515, -0.09], "hrsPerCig": 23},
  {"point": [51.51, -0.09], "hrsPerCig": 20}
]};

var dummy = { "data": [
  { "lat": 51.505,   "long": -0.09,    "AQI": 250 },
  { "lat": 51.506,   "long": -0.091,   "AQI": 300 },
  { "lat": 51.504,   "long": -0.089,   "AQI": 200 },
  { "lat": 51.5055,  "long": -0.092,   "AQI": 350 },
  { "lat": 51.5045,  "long": -0.088,   "AQI": 150 },
  { "lat": 51.5052,  "long": -0.0915,  "AQI": 400 },
  { "lat": 51.5048,  "long": -0.0885,  "AQI": 250 },
  { "lat": 51.5051,  "long": -0.0905,  "AQI": 300 },
  { "lat": 51.5053,  "long": -0.0895,  "AQI": 350 },
  { "lat": 51.5047,  "long": -0.0902,  "AQI": 200 },
  { "lat": 51.5056,  "long": -0.0898,  "AQI": 450 },
  { "lat": 51.5044,  "long": -0.0906,  "AQI": 250 },
  { "lat": 51.5054,  "long": -0.0912,  "AQI": 300 },
  { "lat": 51.5046,  "long": -0.0893,  "AQI": 350 },
  { "lat": 51.505,   "long": -0.0908,  "AQI": 400 },
  { "lat": 51.5052,  "long": -0.0901,  "AQI": 450 },
  { "lat": 51.5049,  "long": -0.0897,  "AQI": 300 },
  { "lat": 51.5053,  "long": -0.0903,  "AQI": 350 },
  { "lat": 51.5048,  "long": -0.0904,  "AQI": 400 },
  { "lat": 51.5051,  "long": -0.0899,  "AQI": 450 }
]};

var heat = getHeatMapLayer(dummy).addTo(map)

addCigMarkersToMap(dummyCig, map)