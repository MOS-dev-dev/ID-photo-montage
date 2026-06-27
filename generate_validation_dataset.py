import os
import cv2
import glob
import numpy as np
import random
import shutil

SOURCE_DIRS = ['anh_nam_tre', 'anh_nam_gia', 'anh_nu_tre', 'anh_nu_gia']
TARGET_BASE = 'validation_dataset'
CATEGORIES = {
    'male_young': 100,
    'male_middle': 100,
    'female_young': 100,
    'female_middle': 100,
    'low_quality': 100,
    'overexposed': 100,
    'underexposed': 100,
    'partially_occluded': 100
}

def get_all_source_images():
    files = []
    for d in SOURCE_DIRS:
        if os.path.exists(d):
            for ext in ('*.png', '*.jpg', '*.jpeg'):
                files.extend(glob.glob(os.path.join(d, ext)))
    return files

def apply_augmentation(img, category):
    if category == 'low_quality':
        # Blur and noise
        img = cv2.GaussianBlur(img, (9, 9), 0)
        noise = np.random.normal(0, 25, img.shape).astype(np.uint8)
        img = cv2.add(img, noise)
    elif category == 'overexposed':
        # Increase brightness
        img = cv2.convertScaleAbs(img, alpha=1.2, beta=50)
    elif category == 'underexposed':
        # Decrease brightness
        img = cv2.convertScaleAbs(img, alpha=0.8, beta=-50)
    elif category == 'partially_occluded':
        # Draw a black rectangle on bottom right
        h, w, _ = img.shape
        cv2.rectangle(img, (int(w*0.5), int(h*0.5)), (w, h), (0, 0, 0), -1)
    return img

def main():
    if not os.path.exists(TARGET_BASE):
        os.makedirs(TARGET_BASE)
        
    src_files = get_all_source_images()
    if not src_files:
        print("No source images found!")
        return
        
    print(f"Found {len(src_files)} source images. Generating 800 validation images...")
    
    for cat, count in CATEGORIES.items():
        cat_dir = os.path.join(TARGET_BASE, cat)
        os.makedirs(cat_dir, exist_ok=True)
        
        # Pick source files based on category if possible
        pool = src_files
        if 'male' in cat:
            pool = [f for f in src_files if 'nam' in f]
        elif 'female' in cat:
            pool = [f for f in src_files if 'nu' in f]
            
        if not pool: pool = src_files
        
        for i in range(count):
            src_file = random.choice(pool)
            img_array = np.fromfile(src_file, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            img_aug = apply_augmentation(img, cat)
            
            out_file = os.path.join(cat_dir, f"{cat}_{i:03d}.jpg")
            # Save using numpy to support unicode paths just in case, though cat is ascii
            is_success, buffer = cv2.imencode(".jpg", img_aug)
            if is_success:
                with open(out_file, "wb") as f:
                    f.write(buffer)
                    
        print(f"Generated {count} images for {cat}")
        
    print("Dataset generation complete!")

if __name__ == "__main__":
    main()
