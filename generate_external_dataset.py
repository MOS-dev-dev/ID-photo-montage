import os
import cv2
import glob
import numpy as np
import random

SOURCE_DIRS = ['anh_nam_tre', 'anh_nam_gia', 'anh_nu_tre', 'anh_nu_gia']
EXTERNAL_DIR = 'external_dataset'
COUNT = 100

def get_all_source_images():
    files = []
    for d in SOURCE_DIRS:
        if os.path.exists(d):
            for ext in ('*.png', '*.jpg', '*.jpeg'):
                files.extend(glob.glob(os.path.join(d, ext)))
    return files

def apply_unseen_augmentation(img):
    # Apply completely different augmentations to simulate "unseen" data
    # 1. Flip horizontal
    if random.random() > 0.5:
        img = cv2.flip(img, 1)
        
    # 2. Color shift
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    h = (h + random.randint(10, 30)) % 180
    s = cv2.add(s, random.randint(-20, 20))
    hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    # 3. Slight rotation
    angle = random.uniform(-10, 10)
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    
    return img

def main():
    os.makedirs(EXTERNAL_DIR, exist_ok=True)
    src_files = get_all_source_images()
    
    if not src_files:
        print("No source images found!")
        return
        
    print(f"Generating {COUNT} external unseen images...")
    
    for i in range(COUNT):
        src_file = random.choice(src_files)
        img_array = np.fromfile(src_file, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        img_aug = apply_unseen_augmentation(img)
        out_file = os.path.join(EXTERNAL_DIR, f"ext_{i:03d}.jpg")
        
        is_success, buffer = cv2.imencode(".jpg", img_aug)
        if is_success:
            with open(out_file, "wb") as f:
                f.write(buffer)
                
    print(f"External dataset generation complete! ({COUNT} images)")

if __name__ == "__main__":
    main()
