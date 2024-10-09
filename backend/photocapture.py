from flask import Flask, request, jsonify
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os
from flask_cors import CORS
import json  # Add this import for JSON handling

app = Flask(__name__)
CORS(app)


# Define the folder to store uploaded images
UPLOAD_FOLDER = 'images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Define the file to store GPS data
GPS_DATA_FILE = 'gps_data.json'

# Function to extract EXIF data from an image
def get_exif_data(image):
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            tag_name = TAGS.get(tag, tag)
            exif_data[tag_name] = value
    return exif_data

# Function to get the GPS data
def get_geotagging(exif_data):
    if 'GPSInfo' in exif_data:
        geotagging = {}
        for key in exif_data['GPSInfo'].keys():
            decode = GPSTAGS.get(key, key)
            geotagging[decode] = exif_data['GPSInfo'][key]
        return geotagging
    return None

# Function to convert GPS coordinates from DMS to decimal format
def get_decimal_from_dms(dms, ref):
    degrees = float(dms[0])
    minutes = float(dms[1]) / 60.0
    seconds = float(dms[2]) / 3600.0
    decimal = degrees + minutes + seconds
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

# Load existing GPS data (if available)
def load_gps_data():
    if os.path.exists(GPS_DATA_FILE):
        with open(GPS_DATA_FILE, 'r') as file:
            return json.load(file)
    return []

# Save GPS data to file
def save_gps_data(data):
    existing_data = load_gps_data()
    existing_data.extend(data)
    with open(GPS_DATA_FILE, 'w') as file:
        json.dump(existing_data, file)

# Home route
@app.route('/')
def home():
    return "Welcome to the Photo Capture API!"

@app.route('/get_image_gps', methods=['GET'])
def get_image_gps():
    # Load GPS data from the file
    gps_data = load_gps_data()
    return jsonify(gps_data)


# API to upload a photo and extract location data
@app.route('/upload', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('file')
    results = []
    gps_data = []  # Initialize a list to store GPS data

    for file in files:
        if file.filename == '':
            continue

        # Save the file to the images folder
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

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

if __name__ == '__main__':
    app.run(debug=True)