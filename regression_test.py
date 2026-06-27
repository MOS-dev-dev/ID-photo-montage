import os
import sys
import glob
import json
import numpy as np
from PIL import Image
import cv2
from tool_tao_the import process_portrait
from generate_golden_outputs import extract_metrics

GOLDEN_DIR = 'golden_dataset'
GOLDEN_OUT = 'golden_outputs'
METRICS_FILE = 'golden_metrics.json'
STATS_FILE = 'detector_stats.json'

def images_identical(img1, img2):
    return np.array_equal(np.array(img1), np.array(img2))

def main():
    if not os.path.exists(METRICS_FILE):
        print(f"Error: {METRICS_FILE} not found. Run generate_golden_outputs.py first.")
        sys.exit(1)
        
    with open(METRICS_FILE, 'r') as f:
        golden_metrics = json.load(f)
        
    files = glob.glob(os.path.join(GOLDEN_DIR, '*.jpg'))
    
    detector_stats = {
        "landmarker": 0,
        "landmarker_recovery": 0,
        "mediapipe_detection": 0,
        "opencv_dnn": 0,
        "pseudo_landmark": 0
    }
    
    max_eye_drift = 0.0
    max_height_drift = 0.0
    failed_images = 0
    ghost_mismatch = 0
    
    print("Running Regression Test...")
    
    for f in files:
        base = os.path.basename(f)
        if base not in golden_metrics:
            continue
            
        main_p, ghost_p, reframes, detector = process_portrait(f)
        
        if main_p is None:
            failed_images += 1
            continue
            
        # Update Stats
        if detector == 'mediapipe_landmarker':
            if reframes == 1:
                detector_stats['landmarker'] += 1
            else:
                detector_stats['landmarker_recovery'] += 1
        elif detector == 'mediapipe_detection':
            detector_stats['mediapipe_detection'] += 1
            detector_stats['pseudo_landmark'] += 1
        elif detector == 'opencv_dnn':
            detector_stats['opencv_dnn'] += 1
            detector_stats['pseudo_landmark'] += 1
            
        # Check Metrics Drift
        m = extract_metrics(main_p)
        if m:
            g = golden_metrics[base]
            eye_drift = abs(m["eye_position_y"] - g["eye_position_y"]) / g["eye_position_y"] * 100 if g["eye_position_y"] > 0 else 0
            height_drift = abs(m["face_height"] - g["face_height"]) / g["face_height"] * 100 if g["face_height"] > 0 else 0
            
            max_eye_drift = max(max_eye_drift, eye_drift)
            max_height_drift = max(max_height_drift, height_drift)
            
        # Check Ghost Match
        golden_ghost_path = os.path.join(GOLDEN_OUT, base.replace('.jpg', '_ghost.png'))
        if os.path.exists(golden_ghost_path):
            golden_ghost = Image.open(golden_ghost_path)
            if not images_identical(ghost_p, golden_ghost):
                ghost_mismatch += 1
                
    # Save Stats
    with open(STATS_FILE, 'w') as f:
        json.dump(detector_stats, f, indent=4)
        
    # Evaluate CI Gate
    print("\n--- REGRESSION TEST RESULTS ---")
    print(f"Max Eye Position Drift: {max_eye_drift:.2f}% (Threshold: 2.0%)")
    print(f"Max Face Height Drift: {max_height_drift:.2f}% (Threshold: 2.0%)")
    print(f"Ghost Alignment Mismatches: {ghost_mismatch} (Threshold: 0)")
    
    pseudo_ratio = detector_stats['pseudo_landmark'] / len(files) * 100 if files else 0
    print(f"Pseudo Landmark Usage: {pseudo_ratio:.2f}%")
    
    passed = True
    
    if max_eye_drift > 2.0:
        print("FAIL BUILD: Eye Position Drift exceeds 2% threshold.")
        passed = False
    if max_height_drift > 2.0:
        print("FAIL BUILD: Face Height Drift exceeds 2% threshold.")
        passed = False
    if ghost_mismatch > 0:
        print("FAIL BUILD: Ghost Offset is not 0px.")
        passed = False
        
    if pseudo_ratio > 5.0:
        print("WARNING: Pseudo Landmark Usage exceeded 5%.")
        
    if not passed:
        sys.exit(1)
        
    print("CI GATE PASSED. READY FOR PRODUCTION.")

if __name__ == "__main__":
    main()
