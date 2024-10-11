from flask import Flask, request, jsonify
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os
from flask_cors import CORS
import json
import subprocess
import abc
from collections import defaultdict
from math import radians, sin, cos, sqrt, atan2
from geopy.geocoders import Nominatim
import geopy.exc

app = Flask(__name__)
CORS(app)

# Define constants
UPLOAD_FOLDER = 'images'
GPS_DATA_FILE = 'gps_data.json'

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
        with open('map_data.json', 'w') as f:
            json.dump(data, f)

    def load_data(self):
        if os.path.exists('map_data.json'):
            with open('map_data.json', 'r') as f:
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

def get_exif_data(image):
    """Extract EXIF data from an image."""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            tag_name = TAGS.get(tag, tag)
            exif_data[tag_name] = value
    return exif_data

def get_geotagging(exif_data):
    """Extract GPS data from EXIF data."""
    if 'GPSInfo' in exif_data:
        geotagging = {}
        for key in exif_data['GPSInfo'].keys():
            decode = GPSTAGS.get(key, key)
            geotagging[decode] = exif_data['GPSInfo'][key]
        return geotagging
    return None

def get_decimal_from_dms(dms, ref):
    """Convert GPS coordinates from DMS to decimal format."""
    degrees = float(dms[0])
    minutes = float(dms[1]) / 60.0
    seconds = float(dms[2]) / 3600.0
    decimal = degrees + minutes + seconds
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

class GPSExtractor:
    def extract(self, file_path):
        file_type = self.get_file_type(file_path)
        extractor = self.get_extractor(file_type)
        return extractor.extract_gps(file_path)

    def get_file_type(self, file_path):
        _, extension = os.path.splitext(file_path.lower())
        return extension[1:]  # Remove the leading dot

    def get_extractor(self, file_type):
        extractors = {
            'jpg': JPEGExtractor(),
            'jpeg': JPEGExtractor(),
            'mov': MOVExtractor(),
        }
        return extractors.get(file_type, NullExtractor())

class BaseExtractor(abc.ABC):
    @abc.abstractmethod
    def extract_gps(self, file_path):
        pass

class JPEGExtractor(BaseExtractor):
    def extract_gps(self, file_path):
        try:
            image = Image.open(file_path)
            exif_data = get_exif_data(image)
            geotagging = get_geotagging(exif_data)
            if geotagging:
                lat = get_decimal_from_dms(geotagging['GPSLatitude'], geotagging['GPSLatitudeRef'])
                lon = get_decimal_from_dms(geotagging['GPSLongitude'], geotagging['GPSLongitudeRef'])
                return GPS(lat, lon)
        except Exception as e:
            print(f"Error extracting GPS from image {file_path}: {e}")
        return None

class MOVExtractor(BaseExtractor):
    def extract_gps(self, file_path):
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_entries', 'format_tags',
                file_path
            ], capture_output=True, text=True)
            
            metadata = json.loads(result.stdout)
            location_tag = metadata['format']['tags'].get('com.apple.quicktime.location.ISO6709')

            if location_tag:
                lat, lon = location_tag[:8], location_tag[8:17]
                return GPS(float(lat), float(lon))
        except Exception as e:
            print(f"Error extracting GPS data from MOV: {e}")
        return None

class NullExtractor(BaseExtractor):
    def extract_gps(self, file_path):
        return None

map_view = MapView()
gps_extractor = GPSExtractor()
location_tracker = LocationTracker("user1", map_view)

@app.route('/')
def home():
    return "Welcome to the Photo Capture API!"

@app.route('/upload', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        gps_data = gps_extractor.extract(file_path)
        
        if gps_data:
            photo = Photo(file_path, gps_data)
            
            # Check if photo already exists before adding
            existing_photos = [p for p in map_view.collections.values() for p in p if p.file_path == file_path]
            if not existing_photos:
                map_view.create_collections([photo])
            
            # Check for nearby photos
            nearby_photos = map_view.get_photos_in_radius((gps_data.lat, gps_data.lon), 0.2)  # 0.2 km radius
            
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

if __name__ == '__main__':
    app.run(debug=True)
