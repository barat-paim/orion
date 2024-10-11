from flask import Flask, request, jsonify, make_response
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os
from flask_cors import CORS
import json
import subprocess
import abc

app = Flask(__name__)
CORS(app)

# Define constants
UPLOAD_FOLDER = 'images'
GPS_DATA_FILE = 'gps_data.json'

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def load_gps_data():
    """Load existing GPS data from file."""
    # Example: Load data from a file or database
    gps_data = ...  # Load your data here
    print("Loaded GPS data:", gps_data)  # Add this line
    if os.path.exists(GPS_DATA_FILE):
        with open(GPS_DATA_FILE, 'r') as file:
            return json.load(file)
    return []

def save_gps_data(data):
    """Save GPS data to file."""
    existing_data = load_gps_data()
    existing_data.extend(data)
    with open(GPS_DATA_FILE, 'w') as file:
        json.dump(existing_data, file)

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
                return lat, lon
        except Exception as e:
            print(f"Error extracting GPS from image {file_path}: {e}")
        return None, None

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
                return float(lat), float(lon)
        except Exception as e:
            print(f"Error extracting GPS data from MOV: {e}")
        return None, None

class NullExtractor(BaseExtractor):
    def extract_gps(self, file_path):
        return None, None

def update_gps_data():
    gps_data = []
    extractor = GPSExtractor()
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        lat, lon = extractor.extract(file_path)
        if lat is not None and lon is not None:
            gps_data.append({
                "filename": filename,
                "latitude": lat,
                "longitude": lon
            })

    with open(GPS_DATA_FILE, 'w') as file:
        json.dump(gps_data, file, indent=4)
    print("Updated GPS data:", gps_data)

@app.route('/')
def home():
    return "Welcome to the Photo Capture API!"

@app.route('/get_image_gps', methods=['GET'])
def get_image_gps():
    update_gps_data()
    with open(GPS_DATA_FILE, 'r') as file:
        gps_data = json.load(file)
    response = make_response(jsonify(gps_data))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/upload', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('file')
    results = []
    gps_data = []
    extractor = GPSExtractor()

    for file in files:
        if file.filename == '':
            continue

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        lat, lon = extractor.extract(file_path)
        if lat is not None and lon is not None:
            gps_data.append({
                "image": file.filename,
                "latitude": lat,
                "longitude": lon
            })
            results.append({
                "filename": file.filename,
                "latitude": lat,
                "longitude": lon,
                "message": "File uploaded and geotagging data extracted successfully!"
            })
        else:
            results.append({
                "filename": file.filename,
                "message": "File uploaded, but no geotagging data found."
            })

    save_gps_data(gps_data)
    return jsonify(results), 200

if __name__ == '__main__':
    app.run(debug=True)