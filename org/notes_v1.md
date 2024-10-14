### Orion Project: Memory Map Application

#### Overview
The Orion project is a memory map application that allows users to upload images with GPS coordinates and display their locations on a map using Leaflet.js.

#### Directory Structure
```
orion/
├── backend/
│   ├── photocapture.py         # Flask server for file uploads and GPS extraction
│   ├── gps_data.json           # Stores extracted GPS data
│   ├── images/                 # Directory for uploaded images
│   ├── requirements.txt        # Python dependencies
├── frontend/
│   ├── index.html              # Main HTML file for map display
│   ├── leaflet.js              # Leaflet.js for map rendering
├── upload_images.sh            # Script for uploading images
├── venv/                       # Python virtual environment
└── README.md                   # Project documentation
```

#### Backend Components
- **photocapture.py**: Handles image uploads, GPS data extraction, and provides API endpoints.
  - **Key Functions**:
    - `get_exif_data(image)`: Extracts EXIF metadata.
    - `get_geotagging(exif_data)`: Retrieves GPS data.
    - `get_decimal_from_dms(dms, ref)`: Converts DMS to decimal degrees.
  - **API Endpoints**:
    - `/upload`: Handles image uploads.
    - `/get_image_gps`: Fetches GPS data for images.

#### Frontend Components
- **index.html**: Displays the map using Leaflet.js.
  - **Key Script**:
    - Fetches GPS data from `/get_image_gps` and adds map markers.

#### Workflow
1. **Image Upload**: Users upload images via a script or web form. The backend processes and stores them.
2. **GPS Data Extraction**: Extracts and converts GPS data from image EXIF metadata.
3. **Serve GPS Data**: Provides GPS data to the frontend via `/get_image_gps`.
4. **Map Display**: Leaflet.js displays a map with markers for each image location.

#### Testing & Usage
1. **Activate Environment**: `source venv/bin/activate`
2. **Run Server**: `python backend/photocapture.py`
3. **Upload Images**: Use `upload_images.sh` or cURL.
4. **View Map**: Open `frontend/index.html` in a browser.

#### Dependencies
- Flask
- Pillow
- Flask-CORS
- Leaflet.js

This setup enables users to upload images, extract GPS data, and visualize photo locations on a map.