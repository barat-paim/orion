from flask import Flask, request, jsonify
import os
from flask_cors import CORS
import json
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2
from geopy.geocoders import Nominatim
import geopy.exc
from extract_gps import extract_gps, GPSData
from clustering import PhotoClusterer
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Define constants
UPLOAD_FOLDER = 'images'
GPS_DATA_FILE = 'map_data.json'
photo_clusterer = PhotoClusterer()

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class GPS:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

class Photo:
    def __init__(self, file_path, gps):
        self.file_path = file_path
        self.gps = gps
        self.location_details = None
        self.geolocator = Nominatim(user_agent="memory_map_app")

    def fetch_location_details(self):
        if not self.location_details:
            try:
                location = self.geolocator.reverse(f"{self.gps.lat}, {self.gps.lon}", timeout=5)
                self.location_details = location.raw['address'] if location else None
            except (geopy.exc.GeocoderTimedOut, geopy.exc.GeocoderUnavailable):
                self.location_details = "Location details unavailable"
        return self.location_details

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "latitude": self.gps.lat,
            "longitude": self.gps.lon,
            "location_details": self.location_details
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['file_path'], GPS(data['latitude'], data['longitude']))

class MapView:
    def __init__(self):
        self.collections = defaultdict(list)
        self.load_data()

    def create_collections(self, photos):
        for photo in photos:
            location = self.get_location_key(photo.gps)
            if not any(p.file_path == photo.file_path for p in self.collections[location]):
                self.collections[location].append(photo)
        self.save_data()

    def get_location_key(self, gps):
        return (round(gps.lat, 5), round(gps.lon, 5))

    def get_photos_for_location(self, location):
        return self.collections.get(location, [])

    def get_photos_in_radius(self, center, radius_km=0.2):
        nearby_photos = []
        for photos in self.collections.values():
            for photo in photos:
                if self.haversine_distance(center, (photo.gps.lat, photo.gps.lon)) <= radius_km:
                    nearby_photos.append(photo)
        return nearby_photos

    def save_data(self):
        data = {str(k): [p.to_dict() for p in v] for k, v in self.collections.items()}
        with open(GPS_DATA_FILE, 'w') as f:
            json.dump(data, f)

    def load_data(self):
        if os.path.exists(GPS_DATA_FILE):
            with open(GPS_DATA_FILE, 'r') as f:
                data = json.load(f)
            for k, v in data.items():
                location = tuple(map(float, k.strip('()').split(', ')))
                self.collections[location] = [Photo.from_dict(p) for p in v]

    @staticmethod
    def haversine_distance(coord1, coord2):
        R = 6371  # Earth radius in kilometers

        lat1, lon1 = map(radians, coord1)
        lat2, lon2 = map(radians, coord2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

class LocationTracker:
    def __init__(self, user, map_view):
        self.user = user
        self.map_view = map_view
        self.last_location = None

    def update_location(self, new_location):
        if self.location_changed(new_location):
            self.last_location = new_location
            return self.check_nearby_photos()

    def location_changed(self, new_location):
        if not self.last_location:
            return True
        return MapView.haversine_distance(self.last_location, new_location) > 0.1  # 100 meters

    def check_nearby_photos(self):
        nearby_photos = self.map_view.get_photos_in_radius(self.last_location, 1)  # 1 km radius
        return nearby_photos if nearby_photos else None

map_view = MapView()
location_tracker = LocationTracker("user1", map_view)

# Initialize an empty list to store all photos
all_photos = []

# App Routes
@app.route('/')
def home():
    return "Welcome to the Photo Capture API!"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        gps_data = extract_gps(file_path)
        
        if gps_data:
            photo = Photo(file_path, GPS(gps_data.latitude, gps_data.longitude))
            
            # Check if photo already exists before adding
            existing_photos = [p for p in map_view.collections.values() for p in p if p.file_path == file_path]
            if not existing_photos:
                map_view.create_collections([photo])
            
            # Check for nearby photos
            nearby_photos = map_view.get_photos_in_radius((gps_data.latitude, gps_data.longitude), 0.2)  # 0.2 km radius
            
            response_data = {
                "message": "File uploaded successfully",
                "data": photo.to_dict(),
                "nearby_photos": [p.to_dict() for p in nearby_photos if p.file_path != file_path]
            }
            
            if nearby_photos:
                response_data["notification"] = f"You have {len(response_data['nearby_photos'])} photos taken within 200 meters!"
            
            try:
                location_details = photo.fetch_location_details()
                if location_details and location_details != "Location details unavailable":
                    response_data["notification"] += f"<br>You took this photo at: {location_details}"
            except Exception as e:
                app.logger.error(f"Error fetching location details: {str(e)}")
            
            # After successfully processing the uploaded file, add it to all_photos
            all_photos.append({
                'file_path': file_path,
                'latitude': gps_data.latitude,
                'longitude': gps_data.longitude
            })
            
            return jsonify(response_data), 200
        else:
            return jsonify({"error": "No GPS data found in the image"}), 400

@app.route('/get_image_gps', methods=['GET'])
def get_image_gps():
    all_photos = []
    for photos in map_view.collections.values():
        all_photos.extend([photo.to_dict() for photo in photos])
    return jsonify(all_photos)

@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.json
    new_location = (data['latitude'], data['longitude'])
    nearby_photos = location_tracker.update_location(new_location)
    
    if nearby_photos:
        return jsonify({
            "message": f"You have {len(nearby_photos)} photos taken nearby!",
            "nearby_photos": [photo.to_dict() for photo in nearby_photos]
        }), 200
    else:
        return jsonify({"message": "No nearby photos found"}), 200

@app.route('/get_clustered_photos', methods=['GET'])
def get_clustered_photos():
    global all_photos  # Declare that we're using the global variable
    
    zoom_level = int(request.args.get('zoom', 10))
    
    # Get map bounds, use None if not provided
    ne_lat = request.args.get('ne_lat')
    ne_lng = request.args.get('ne_lng')
    sw_lat = request.args.get('sw_lat')
    sw_lng = request.args.get('sw_lng')

    # Convert to float if provided, otherwise use None
    ne_lat = float(ne_lat) if ne_lat is not None else None
    ne_lng = float(ne_lng) if ne_lng is not None else None
    sw_lat = float(sw_lat) if sw_lat is not None else None
    sw_lng = float(sw_lng) if sw_lng is not None else None

    # Filter photos within the current map bounds if bounds are provided
    if all([ne_lat, ne_lng, sw_lat, sw_lng]):
        visible_photos = [photo for photo in all_photos if 
                          sw_lat <= photo['latitude'] <= ne_lat and 
                          sw_lng <= photo['longitude'] <= ne_lng]
    else:
        visible_photos = all_photos  # Use all photos if bounds are not provided

    clustered_photos = photo_clusterer.cluster_photos(visible_photos, zoom_level)
    return jsonify(clustered_photos)

if __name__ == '__main__':
    app.run(debug=True)
