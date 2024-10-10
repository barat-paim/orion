from flask import Flask, request, jsonify, make_response
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os
from flask_cors import CORS
import json
import subprocess

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

def get_gps_from_mov(filepath):
    try:
        # Run ffprobe to extract the location data
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_entries', 'format_tags',
            filepath
        ], capture_output=True, text=True)
        
        # Parse the JSON output
        metadata = json.loads(result.stdout)
        location_tag = metadata['format']['tags'].get('com.apple.quicktime.location.ISO6709')

        if location_tag:
            # Extract latitude and longitude from ISO6709 format
            lat, lon = location_tag[:8], location_tag[8:17]  # Adjust slicing based on format
            lat, lon = float(lat), float(lon)
            return lat, lon
        else:
            return None, None
    except Exception as e:
        print(f"Error extracting GPS data from MOV: {e}")
        return None, None

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

    for file in files:
        if file.filename == '':
            continue

        # Save the file to the images folder
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Check if the file is a MOV
        if file.filename.lower().endswith('.mov'):
            lat, lon = get_gps_from_mov(file_path)
            if lat and lon:
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
                    "message": "File uploaded, but no geotagging data found in video."
                })
        else:
            # Existing JPEG/EXIF processing logic
            try:
                image = Image.open(file_path)
                exif_data = get_exif_data(image)
                geotagging = get_geotagging(exif_data)

                if geotagging:
                    lat = get_decimal_from_dms(geotagging['GPSLatitude'], geotagging['GPSLatitudeRef'])
                    lon = get_decimal_from_dms(geotagging['GPSLongitude'], geotagging['GPSLongitudeRef'])
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
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "error": str(e)
                })

    # Save the GPS data to the file
    save_gps_data(gps_data)

    return jsonify(results), 200

def update_gps_data():
    gps_data = []
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if filename.lower().endswith(('.jpeg', '.jpg')):
            lat, lon = extract_gps_data_from_image(file_path)
        elif filename.lower().endswith('.mov'):
            lat, lon = get_gps_from_mov(file_path)
        else:
            continue

        if lat is not None and lon is not None:
            gps_data.append({
                "filename": filename,
                "latitude": lat,
                "longitude": lon
            })

    with open(GPS_DATA_FILE, 'w') as file:
        json.dump(gps_data, file, indent=4)
    print("Updated GPS data:", gps_data)

def extract_gps_data_from_image(file_path):
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

if __name__ == '__main__':
    app.run(debug=True)