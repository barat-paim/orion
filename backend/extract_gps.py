import sys
import os
from abc import ABC, abstractmethod
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import piexif
from fractions import Fraction
import ffmpeg
import logging

# Add this near the top of your script
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GPSData:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

class GPSExtractor(ABC):
    @abstractmethod
    def extract(self, file_path):
        pass

    @staticmethod
    def _convert_to_degrees(value):
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)

class JPEGExtractor(GPSExtractor):
    def extract(self, file_path):
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return None

            gps_info = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "GPSInfo":
                    for key in value:
                        sub_tag = GPSTAGS.get(key, key)
                        gps_info[sub_tag] = value[key]

            if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
                lat = self._convert_to_degrees(gps_info["GPSLatitude"])
                lon = self._convert_to_degrees(gps_info["GPSLongitude"])
                if gps_info["GPSLatitudeRef"] == "S":
                    lat = -lat
                if gps_info["GPSLongitudeRef"] == "W":
                    lon = -lon
                return GPSData(lat, lon)
        return None

class HEICExtractor(GPSExtractor):
    def extract(self, file_path):
        try:
            exif_dict = piexif.load(file_path)
            gps_data = exif_dict.get('GPS', {})
            
            if 2 in gps_data and 4 in gps_data:  # Check if latitude and longitude exist
                lat = self._convert_to_degrees([Fraction(v).limit_denominator() for v in gps_data[2]])
                lon = self._convert_to_degrees([Fraction(v).limit_denominator() for v in gps_data[4]])
                
                if gps_data.get(1) == b'S':
                    lat = -lat
                if gps_data.get(3) == b'W':
                    lon = -lon
                
                return GPSData(lat, lon)
        except Exception as e:
            print(f"Error extracting GPS data from HEIC: {e}")
        return None

class MOVExtractor(GPSExtractor):
    def extract(self, file_path):
        try:
            logger.debug(f"Attempting to extract GPS data from MOV file: {file_path}")
            probe = ffmpeg.probe(file_path)
            logger.debug(f"FFprobe result: {probe}")
            
            if 'format' in probe and 'tags' in probe['format']:
                tags = probe['format']['tags']
                logger.debug(f"Format tags: {tags}")
                
                if 'com.apple.quicktime.location.ISO6709' in tags:
                    location = tags['com.apple.quicktime.location.ISO6709']
                    logger.debug(f"Found Apple QuickTime location tag: {location}")
                    # Parse the ISO6709 format: +40.7685-073.9868+033.150/
                    parts = location.split('+')
                    lat = float(parts[1].split('-')[0])
                    lon = -float(parts[1].split('-')[1].split('+')[0])  # Longitude is negative
                    return GPSData(lat, lon)
            
            logger.warning("No recognized GPS tags found in metadata")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting GPS data from MOV: {e}")
            return None

class GPSExtractorFactory:
    @staticmethod
    def get_extractor(file_path):
        _, ext = os.path.splitext(file_path.lower())
        if ext in ['.jpg', '.jpeg']:
            return JPEGExtractor()
        elif ext == '.heic':
            return HEICExtractor()
        elif ext == '.mov':
            return MOVExtractor()
        else:
            raise ValueError(f"Unsupported file format: {ext}")

def extract_gps(file_path):
    try:
        extractor = GPSExtractorFactory.get_extractor(file_path)
        return extractor.extract(file_path)
    except ValueError as e:
        print(f"Error: {e}")
        return None

# Example usage
if __name__ == "__main__":
    # Use a default relative path if no argument is provided
    default_path = os.path.join(script_dir, 'images', 'apples.jpeg')
    file_path = sys.argv[1] if len(sys.argv) > 1 else default_path

    # Get the absolute path
    abs_file_path = os.path.abspath(file_path)

    if not os.path.exists(abs_file_path):
        print(f"Error: File '{abs_file_path}' does not exist.")
        sys.exit(1)
    
    gps_data = extract_gps(abs_file_path)
    if gps_data:
        print(f"Extracted GPS Data: Latitude {gps_data.latitude}, Longitude {gps_data.longitude}")
    else:
        print("No GPS data found or extraction failed.")
