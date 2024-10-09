<!DOCTYPE html>
<html>
<head>
    <title>Memory Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
</head>
<body>
    <div id="map" style="height: 500px;"></div>
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([51.505, -0.09], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Fetch photo coordinates and add marker to map
        fetch('/upload').then(response => response.json()).then(data => {
            var marker = L.marker([data.latitude, data.longitude]).addTo(map)
                .bindPopup(`<b>${data.filename}</b><br>${data.latitude}, ${data.longitude}`).openPopup();
        });
    </script>
</body>
</html>