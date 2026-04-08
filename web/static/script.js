let map = L.map('map', {
    center: [40.7549, -73.9840],
    zoom: 14,
    dragging: false
});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

let orderMarkers = [];
let vehicleMarkers = [];

let chart = new Chart(document.getElementById("chart"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "Reward",
            data: []
        }]
    }
});

function drawState(data) {

    orderMarkers.forEach(m => map.removeLayer(m));
    vehicleMarkers.forEach(m => map.removeLayer(m));

    orderMarkers = [];
    vehicleMarkers = [];

    data.orders.forEach(o => {
        let m = L.circleMarker([o.lat, o.lon]).addTo(map);
        orderMarkers.push(m);
    });

    data.vehicles.forEach(v => {
        let m = L.marker([v.lat, v.lon]).addTo(map);
        vehicleMarkers.push(m);
    });

    updateMetrics(data.metrics);
}

function updateMetrics(m) {
    if (!m) return;

    document.getElementById("reward").innerText = m.reward || 0;
    document.getElementById("score").innerText = (m.score || 0).toFixed(2);
    document.getElementById("delivery").innerText =
        (m.delivery_rate || 0).toFixed(2);

    if (m.time !== undefined) {
        chart.data.labels.push(m.time);
        chart.data.datasets[0].data.push(m.reward || 0);
        chart.update();
    }
}

async function stepSimulation() {
    const res = await fetch("/step");
    const data = await res.json();

    drawState(data);

    setTimeout(stepSimulation, 500);
}

async function resetSimulation() {
    let vehicles = document.getElementById("vehicles").value;

    await fetch("/reset", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({vehicles: parseInt(vehicles)})
    });
}

map.on("click", async function(e) {
    await fetch("/add_order", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            lat: e.latlng.lat,
            lon: e.latlng.lng
        })
    });
});

stepSimulation();