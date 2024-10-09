#!/bin/bash

# Directory containing the images
IMAGE_DIR="./images"

# URL of the upload endpoint
UPLOAD_URL="http://127.0.0.1:5000/upload"

# Check if the directory exists
if [ ! -d "$IMAGE_DIR" ]; then
  echo "Directory $IMAGE_DIR does not exist."
  exit 1
fi

# Loop through each image in the directory
for image in "$IMAGE_DIR"/*; do
  # Check if the file exists and is readable
  if [ ! -f "$image" ]; then
    echo "File $image does not exist or is not a regular file."
    continue
  fi

  echo "Uploading $image"
  # Use curl to upload each image
  curl -X POST -F "file=@$image" "$UPLOAD_URL"
done