### Minimal Documentation for Orion Project

#### Project Overview:
The Orion project is a memory map application that allows users to upload images with embedded GPS coordinates (EXIF data) and display the images' locations on a map. The system extracts location data from uploaded images and displays the image locations using the Leaflet.js library on a map.

#### Directory Structure:
```
orion/
│
├── backend/                   # Contains the backend logic and server code
│   ├── photocapture.py         # Flask server for handling file uploads and GPS extraction
│   ├── gps_data.json           # A sample JSON file to store extracted GPS data
│   ├── images/                 # Folder where uploaded images are stored
│   ├── requirements.txt        # Python dependencies (Flask, Pillow, etc.)
│
├── frontend/                   # Contains the front-end files for map display
│   ├── index.html              # Main HTML file that displays the map
│   ├── leaflet.js              # Handles front-end logic using Leaflet.js for map rendering
│
├── upload_images.sh            # Bash script for uploading images via cURL
│
├── venv/                       # Python virtual environment
│
└── README.md                   # Project description and usage documentation
```

#### Backend Components:
- **photocapture.py**: The main Flask application that handles image uploads, extracts GPS data, and provides an API for the frontend to fetch GPS coordinates.

  - Key Variables:
    - `UPLOAD_FOLDER`: Directory where uploaded images are stored.
    - `get_exif_data(image)`: Extracts EXIF metadata from an image.
    - `get_geotagging(exif_data)`: Retrieves GPS data from EXIF metadata.
    - `get_decimal_from_dms(dms, ref)`: Converts GPS coordinates from Degrees-Minutes-Seconds (DMS) format to decimal degrees.
    - `/upload`: API route to handle image uploads.
    - `/get_image_gps`: API route to fetch image GPS data.

#### Frontend Components:
- **index.html**: The main UI where the map is displayed using the Leaflet.js library.
  - Key Script:
    - `fetch('http://127.0.0.1:5000/get_image_gps')`: Fetches GPS data from the backend and adds markers to the map.
  
- **leaflet.js**: Script that interacts with the Leaflet library to render the map, fetch the GPS data, and display markers.

#### Workflow:

1. **Image Upload**: 
   - Users upload one or more images via a script (e.g., `upload_images.sh`) or a web form.
   - The Flask backend (`/upload`) processes the images, extracts GPS coordinates from their EXIF metadata, and stores the images in the `images/` folder.

2. **GPS Data Extraction**:
   - The backend uses `Pillow` to read EXIF data from the uploaded images.
   - If GPS information is found in the image, it extracts the latitude and longitude coordinates and converts them to a decimal format.
   
3. **Serve GPS Data**:
   - The `/get_image_gps` API endpoint provides the GPS data of all uploaded images in JSON format to the frontend.
   
4. **Map Display**:
   - The frontend (`index.html`) uses the Leaflet.js library to display a map.
   - A `fetch` call to the backend retrieves the GPS coordinates and adds markers to the map for each image location.

#### Key Variables in `photocapture.py`:

- **UPLOAD_FOLDER**: The folder where images are saved.
- **exif_data**: Stores the EXIF metadata extracted from an image.
- **geotagging**: Stores the GPS data extracted from EXIF.
- **lat, lon**: Latitude and longitude coordinates in decimal degrees.

#### Testing & Usage:

1. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Run the Flask Server**:
   ```bash
   python backend/photocapture.py
   ```

3. **Upload Images**:
   - Use the `upload_images.sh` script or cURL to upload images.

4. **Access the Map**:
   - Open the `frontend/index.html` file in a browser. You will see the map with markers showing the locations of uploaded images.

#### Dependencies:
- Flask
- Pillow (for image processing)
- Flask-CORS (to handle CORS policy)
- Leaflet.js (for displaying the map)

This setup allows users to upload images, extract GPS data, and view the photo locations on a map.