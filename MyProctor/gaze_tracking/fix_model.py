#!/usr/bin/env python3
"""
Robust script to download and validate the dlib facial landmark model
"""

import os
import urllib.request
import bz2
import shutil
import hashlib

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception:
        return None

def download_with_progress(url, filepath):
    """Download file with progress indicator"""
    def show_progress(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            mb_downloaded = downloaded // 1024 // 1024
            mb_total = total_size // 1024 // 1024
            print(f"\rProgress: {percent:.1f}% ({mb_downloaded}MB/{mb_total}MB)", end='', flush=True)
    
    try:
        urllib.request.urlretrieve(url, filepath, reporthook=show_progress)
        print()  # New line after progress
        return True
    except Exception as e:
        print(f"\nDownload failed: {e}")
        return False

def main():
    # Setup paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(script_dir, "gaze_tracking", "trained_models")
    os.makedirs(model_dir, exist_ok=True)
    
    compressed_file = os.path.join(model_dir, "shape_predictor_68_face_landmarks.dat.bz2")
    model_file = os.path.join(model_dir, "shape_predictor_68_face_landmarks.dat")
    
    # URLs to try (in case one fails)
    urls = [
        "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2",
        "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
    ]
    
    # Expected file size (approximately 95MB for the .dat file)
    expected_min_size = 90 * 1024 * 1024  # 90MB minimum
    
    # Remove existing files if they exist
    for file_path in [compressed_file, model_file]:
        if os.path.exists(file_path):
            print(f"Removing existing file: {file_path}")
            os.remove(file_path)
    
    # Try downloading from each URL
    download_success = False
    for i, url in enumerate(urls, 1):
        print(f"\nAttempt {i}: Downloading from {url}")
        if download_with_progress(url, compressed_file):
            download_success = True
            break
        else:
            print(f"Failed to download from {url}")
    
    if not download_success:
        print("\n❌ All download attempts failed!")
        print("Please try downloading manually:")
        print("1. Go to: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2")
        print("2. Save the file to your Downloads folder")
        print(f"3. Extract and move the .dat file to: {model_dir}")
        return False
    
    # Verify compressed file
    if not os.path.exists(compressed_file):
        print("❌ Downloaded file not found!")
        return False
    
    file_size = os.path.getsize(compressed_file)
    print(f"Downloaded file size: {file_size // 1024 // 1024}MB")
    
    if file_size < 10 * 1024 * 1024:  # Less than 10MB is suspicious
        print("❌ Downloaded file seems too small. It might be corrupted.")
        return False
    
    # Extract the file
    print("Extracting compressed file...")
    try:
        with bz2.BZ2File(compressed_file, 'rb') as f_in:
            with open(model_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        print("✓ Extraction completed!")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return False
    
    # Verify extracted file
    if not os.path.exists(model_file):
        print("❌ Extracted file not found!")
        return False
    
    extracted_size = os.path.getsize(model_file)
    print(f"Extracted file size: {extracted_size // 1024 // 1024}MB")
    
    if extracted_size < expected_min_size:
        print("❌ Extracted file seems too small. It might be corrupted.")
        return False
    
    # Test the model file with dlib
    print("Testing model file with dlib...")
    try:
        import dlib
        predictor = dlib.shape_predictor(model_file)
        print("✓ Model file is valid and loads correctly!")
    except ImportError:
        print("⚠️  Could not import dlib to test the model, but file seems correct")
    except Exception as e:
        print(f"❌ Model file test failed: {e}")
        print("The downloaded file might be corrupted.")
        return False
    
    # Clean up compressed file
    try:
        os.remove(compressed_file)
        print("✓ Cleaned up compressed file")
    except Exception:
        pass
    
    print(f"\n🎉 Success! Model file is ready at:")
    print(f"   {model_file}")
    print("\nYou can now run your application!")
    return True

if __name__ == "__main__":
    main()