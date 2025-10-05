async function fetchData(){
    try{
        console.log("B");
        const response = await fetch("https://18sj5l5uq2.execute-api.eu-north-1.amazonaws.com/airQuality")
        let data = await response.json()
  
        if(!response.ok){
            throw new Error("Failed to fetch data");
        }
        console.log(data)
        return data
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
    intensity = 0.2
  }
  else if (AQI <= 100) {
    intensity = 0.4
  }
  else if (AQI <= 150) {
    intensity = 0.5
  }
  else if (AQI <= 200) {
    intensity = 0.65
  }
  else if (AQI <= 300) {
    intensity = 0.85
  }
  else {intensity = 0.95}
  return intensity
}

function getHeatPointsArray (pointsJson) {
  var points = []
  pointsJson.data.forEach( obj => {
    obj.stationsData.forEach( ob => {
      var intensity = standardizeAQI(ob.AQI);
      var point = [ob.lat, ob.long, intensity];
      points.push(point)
    })
  })
  return points
}

function getHeatMapLayer(pointsJson) {
  var points = getHeatPointsArray(pointsJson);
  var heat = L.heatLayer(points, {radius: 200})
  return heat
}

function getSanFranMap() {
  return L.map('map').setView([28.61, 77.23], 13);
}

function addCigMarkersToMap(jsonData, map) {
  jsonData.data.forEach(obj => {
    L.marker([obj.poi.lat, obj.poi.long])
      .addTo(map)
      .bindPopup(`Breathing the air in this location for ${obj.hrsPerCig} hours is the equivalent of smoking one cigarette!`)
  })
}

function openLegend() {
  document.getElementById("legend").style.display = "flex";
}

function closeLegend() {
  document.getElementById("legend").style.display = "none";
}


async function main() {
  let data = await fetchData();

  var map = getSanFranMap();

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);

  var dummyCig = {"data": [
    {"point": [51.50515, -0.09], "hrsPerCig": 23},
    {"point": [51.51, -0.09], "hrsPerCig": 20}
  ]};

  var heat = getHeatMapLayer(data).addTo(map)

  addCigMarkersToMap(data, map)
}

main()

