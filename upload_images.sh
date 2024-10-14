#!/bin/bash

# Directory containing the images
IMAGE_DIR="./images"

# URL of the upload endpoint
UPLOAD_URL="http://127.0.0.1:5000/upload"

# Check if the directory exists
if [ ! -d "$IMAGE_DIR" ]; then
  echo "Error: Directory $IMAGE_DIR does not exist."
  exit 1
fi

# Counter for successful uploads
successful_uploads=0

# Loop through each image in the directory
for image in "$IMAGE_DIR"/*; do
  # Check if the file exists and is readable
  if [ ! -f "$image" ]; then
    echo "Warning: $image is not a regular file. Skipping."
    continue
  fi

  echo "Uploading $image"
  # Use curl to upload each image and capture the response
  response=$(curl -s -X POST -F "file=@$image" "$UPLOAD_URL")
  
  # Check if the upload was successful
  if echo "$response" | grep -q "File uploaded successfully"; then
    echo "Success: $image uploaded"
    ((successful_uploads++))
  else
    echo "Error: Failed to upload $image"
    echo "Server response: $response"
  fi
  
  echo "---"
done

echo "Upload process completed. $successful_uploads file(s) uploaded successfully."
