import os
from abc import ABC, abstractmethod
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import piexif
from fractions import Fraction
import json
import ffmpeg

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
            probe = ffmpeg.probe(file_path)
            metadata = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            if 'tags' in metadata and 'location' in metadata['tags']:
                location = metadata['tags']['location']
                lat, lon = map(float, location.split('+')[1:3])
                return GPSData(lat, lon)
            
            # If location tag is not present, try to find GPS data in format-specific metadata
            if 'tags' in metadata:
                tags = metadata['tags']
                if 'com.apple.quicktime.location.ISO6709' in tags:
                    location = tags['com.apple.quicktime.location.ISO6709']
                    lat, lon = map(float, location.split('+')[1:3])
                    return GPSData(lat, lon)
                
                # Add more vendor-specific metadata checks here if needed
        
        except Exception as e:
            print(f"Error extracting GPS data from MOV: {e}")
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
