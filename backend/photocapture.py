from flask import Flask, request, jsonify
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import os

app = Flask(__name__)

# Define the folder to store uploaded images
UPLOAD_FOLDER = 'images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

# Home route
@app.route('/')
def home():
    return "Welcome to the Photo Capture API!"

# API to upload a photo and extract location data
@app.route('/upload', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('file')
    results = []

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

    return jsonify(results), 200

if __name__ == '__main__':
    app.run(debug=True)