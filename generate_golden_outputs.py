import os
import glob
import json
import numpy as np
from PIL import Image
import cv2
from tool_tao_the import process_portrait, face_landmarker
import mediapipe as mp

GOLDEN_DIR = 'golden_dataset'
GOLDEN_OUT = 'golden_outputs'
METRICS_FILE = 'golden_metrics.json'

def extract_metrics(main_rgba):
    # Convert RGBA to RGB with white background for MediaPipe
    bg = Image.new("RGB", main_rgba.size, (255, 255, 255))
    bg.paste(main_rgba, mask=main_rgba.split()[3])
    
    img_bgr = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    
    h, w, _ = img_rgb.shape
    
    # 1. Get Head Margin & Face Height from Alpha Channel
    alpha = np.array(main_rgba.split()[3])
    y_indices, x_indices = np.where(alpha > 15)
    
    if len(y_indices) == 0:
        return None
        
    head_margin = int(np.min(y_indices))
    face_height = int(np.max(y_indices) - np.min(y_indices))
    
    # 2. Get Eye Position via MediaPipe
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    res = face_landmarker.detect(mp_image)
    
    eye_y = 0
    if res and res.face_landmarks:
        lm = res.face_landmarks[0]
        # Average Y of left eye (159) and right eye (386)
        eye_y = int((lm[159].y + lm[386].y) / 2.0 * h)
        
    return {
        "head_margin": head_margin,
        "face_height": face_height,
        "eye_position_y": eye_y
    }

def main():
    os.makedirs(GOLDEN_OUT, exist_ok=True)
    files = glob.glob(os.path.join(GOLDEN_DIR, '*.jpg'))
    files.sort()
    
    metrics = {}
    print("Generating Golden Outputs and Metrics...")
    
    for idx, f in enumerate(files):
        print(f"Processing {idx+1}/{len(files)}: {f}")
        main_p, ghost_p, reframes, detector = process_portrait(f)
        
        if main_p is None:
            continue
            
        base = os.path.basename(f)
        main_path = os.path.join(GOLDEN_OUT, base.replace('.jpg', '_main.png'))
        ghost_path = os.path.join(GOLDEN_OUT, base.replace('.jpg', '_ghost.png'))
        
        main_p.save(main_path)
        ghost_p.save(ghost_path)
        
        m = extract_metrics(main_p)
        if m:
            metrics[base] = m
            
    with open(METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Golden Generation Complete. Saved metrics for {len(metrics)} images.")

if __name__ == "__main__":
    main()
