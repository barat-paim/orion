Here's the command line process for running the frontend and backend:

1. **Run the Flask backend**:

   ```bash
   cd backend
   python3 photocapture.py
   ```

2. **Run the script to upload the images**:

   After placing images in the `images` folder, run the following script to upload them to the backend:

   ```bash
   ./upload_images.sh
   ```

3. **Run the frontend (HTTP server)**:

   Open a new terminal window, and run the following to start the frontend:

   ```bash
   cd frontend
   python3 -m http.server
   ```

4. **Check if the GPS data is working**:

   After running the frontend and backend, open your browser and visit:

   ```bash
   http://127.0.0.1:8000
   ```

   Check that the map is displaying the correct markers for the uploaded images.

That's it! The terminal commands for testing and running the full flow.