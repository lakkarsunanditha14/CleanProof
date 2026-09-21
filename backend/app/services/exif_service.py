import math
from typing import Tuple, Optional, Dict, Any
import numpy as np
from PIL import Image
import piexif
from datetime import datetime

# DCT-II matrix (as scipy.fftpack.dct), so the hash matches imagehash.phash without SciPy
_N = np.arange(32)
_DCT = 2 * np.cos(np.pi * _N[:, None] * (2 * _N[None, :] + 1) / 64)


def phash_hex(img: Image.Image) -> str:
    """Perceptual hash, identical to str(imagehash.phash(img)): 32x32 grey, DCT, 8x8 low frequencies vs median."""
    pixels = np.asarray(img.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    low = np.round((_DCT @ pixels @ _DCT.T)[:8, :8], 6)  # drop float noise (flat images)
    bits = "".join("1" if b else "0" for b in (low > np.median(low)).flatten())
    return f"{int(bits, 2):016x}"


def calculate_image_hash(image_path: str) -> str:
    """Calculates perceptual hash string (phash) for an image."""
    try:
        with Image.open(image_path) as img:
            return phash_hex(img)
    except Exception as e:
        print(f"Error calculating image hash for {image_path}: {e}")
        return ""

def compare_image_hashes(hash1_str: str, hash2_str: str) -> Optional[int]:
    """Returns Hamming distance between two perceptual hash strings."""
    if not hash1_str or not hash2_str:
        return None
    try:
        return bin(int(hash1_str, 16) ^ int(hash2_str, 16)).count("1")
    except Exception as e:
        print(f"Error comparing hashes ({hash1_str} vs {hash2_str}): {e}")
        return None

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def _convert_to_degrees(value) -> float:
    """Helper to convert EXIF GPS coordinates (tuples) to decimal degrees."""
    d = float(value[0][0]) / float(value[0][1])
    m = float(value[1][0]) / float(value[1][1])
    s = float(value[2][0]) / float(value[2][1])
    return d + (m / 60.0) + (s / 3600.0)

def extract_exif_metadata(image_path: str) -> Dict[str, Any]:
    """
    Extracts EXIF metadata including presence flag, timestamp, and GPS coordinates if available.
    """
    result = {
        "has_exif": False,
        "timestamp": None,
        "latitude": None,
        "longitude": None,
        "raw_exif": {}
    }
    
    try:
        with Image.open(image_path) as img:
            info = img._getexif() if hasattr(img, '_getexif') else None
            
            # Try piexif if PIL _getexif is None or empty
            exif_dict = None
            if "exif" in img.info:
                try:
                    exif_dict = piexif.load(img.info["exif"])
                except Exception:
                    exif_dict = None
                    
            if info or (exif_dict and any(exif_dict.values())):
                result["has_exif"] = True
                
            # Extract timestamp from piexif if available
            if exif_dict:
                if piexif.ExifIFD.DateTimeOriginal in exif_dict.get("Exif", {}):
                    date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode("utf-8")
                    try:
                        result["timestamp"] = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    except Exception:
                        pass
                
                # Extract GPS
                gps_data = exif_dict.get("GPS", {})
                if gps_data:
                    try:
                        if piexif.GPSIFD.GPSLatitude in gps_data and piexif.GPSIFD.GPSLongitude in gps_data:
                            lat = _convert_to_degrees(gps_data[piexif.GPSIFD.GPSLatitude])
                            if gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'N') == b'S':
                                lat = -lat
                            result["latitude"] = lat
                            
                            lon = _convert_to_degrees(gps_data[piexif.GPSIFD.GPSLongitude])
                            if gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'E') == b'W':
                                lon = -lon
                            result["longitude"] = lon
                    except Exception as e:
                        print(f"Error parsing EXIF GPS: {e}")
    except Exception as e:
        print(f"Error processing EXIF for {image_path}: {e}")
        
    return result
