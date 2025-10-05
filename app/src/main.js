function standardizeAQI(AQI) {
  return AQI / 500
}

function getHeatPointsArray (pointsJson) {
  var points = []
  pointsJson.data.forEach( obj => {
    var intensity = standardizeAQI(obj.AQI);
    var point = [obj.lat, obj.long, intensity];
    points.push(point)
  })
  console.log(points)
  return points
}

function getHeatMapLayer(pointsJson) {
  var points = getHeatPointsArray(pointsJson);
  var heat = L.heatLayer(points, {radius: 30})
  return heat
}

function getSanFranMap() {
  return L.map('map').setView([51.505, -0.09], 13);

}

var map = getSanFranMap();

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap'
}).addTo(map);

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

/* var heat = L.heatLayer([
  [51.505, -0.09, 0.5],
  [51.506, -0.091, 0.6],
  [51.504, -0.089, 0.4],
  [51.5055, -0.092, 0.7],
  [51.5045, -0.088, 0.3],
  [51.5052, -0.0915, 0.8],
  [51.5048, -0.0885, 0.5],
  [51.5051, -0.0905, 0.6],
  [51.5053, -0.0895, 0.7],
  [51.5047, -0.0902, 0.4],
  [51.5056, -0.0898, 0.9],
  [51.5044, -0.0906, 0.5],
  [51.5054, -0.0912, 0.6],
  [51.5046, -0.0893, 0.7],
  [51.505, -0.0908, 0.8],
  [51.5052, -0.0901, 0.9],
  [51.5049, -0.0897, 0.6],
  [51.5053, -0.0903, 0.7],
  [51.5048, -0.0904, 0.8],
  [51.5051, -0.0899, 0.9]
], {radius: 25}).addTo(map); */