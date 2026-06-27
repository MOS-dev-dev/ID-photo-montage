import os
import glob
import random
import csv
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tool_tao_the import process_portrait, TEMPLATE_PATH, CFG_MAIN, CFG_GHOST, GHOST_BG_LEFT, GHOST_BG_TOP, HOLO_LEFT, HOLO_TOP

REVIEW_DS = 'review_dataset'
REVIEW_CARDS = 'review_cards'
MANIFEST = 'review_manifest.csv'

def apply_augmentation(img_bgr, target_type):
    h, w, _ = img_bgr.shape
    if target_type == 'direct':
        return img_bgr
    elif target_type == 'recovery':
        # Darken to force Landmarker to fail, but recoverable by CLAHE
        return cv2.convertScaleAbs(img_bgr, alpha=0.3, beta=0)
    elif target_type == 'fallback':
        # Occlude part of the face to force Landmarker to fail, and make it hard for stage 2
        # OpenCV DNN usually handles occlusions better
        img_copy = img_bgr.copy()
        cv2.rectangle(img_copy, (0, h//2), (w//2, h), (0,0,0), -1)
        return cv2.convertScaleAbs(img_copy, alpha=0.5, beta=10)
    elif target_type == 'difficult':
        # Extreme crop and occlusion
        img_copy = img_bgr.copy()
        cv2.rectangle(img_copy, (0, int(h*0.3)), (w, h), (0,0,0), -1)
        return img_copy
    return img_bgr

def main():
    os.makedirs(REVIEW_DS, exist_ok=True)
    os.makedirs(REVIEW_CARDS, exist_ok=True)
    
    src_dirs = ['anh_nam_tre', 'anh_nam_gia', 'anh_nu_tre', 'anh_nu_gia']
    src_files = []
    for d in src_dirs:
        if os.path.exists(d):
            src_files.extend(glob.glob(os.path.join(d, '*.*')))
            
    src_files = [f for f in src_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not src_files:
        print("No source files found!")
        return
        
    print("Generating Review Dataset...")
    
    # 40 direct, 30 recovery, 20 fallback, 10 difficult
    targets = ['direct']*40 + ['recovery']*30 + ['fallback']*20 + ['difficult']*10
    random.shuffle(targets)
    
    for i, t in enumerate(targets):
        src = random.choice(src_files)
        img_array = np.fromfile(src, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        aug = apply_augmentation(img, t)
        out_path = os.path.join(REVIEW_DS, f"{i:03d}_{t}.jpg")
        success, encoded_img = cv2.imencode('.jpg', aug)
        if success:
            encoded_img.tofile(out_path)
        
    print("Generating Review Cards...")
    
    template_img = Image.open(TEMPLATE_PATH).convert("RGBA")
    patch = Image.new('RGBA', (CFG_MAIN["width"], CFG_MAIN["height"]), (0,0,0,0))
    patch_draw = ImageDraw.Draw(patch)
    patch_draw.rounded_rectangle([10, 10, CFG_MAIN["width"]-10, CFG_MAIN["height"]-80], radius=50, fill=(210, 215, 220, 255))
    patch = patch.filter(ImageFilter.GaussianBlur(30))
    template_img.alpha_composite(patch, (CFG_MAIN["x"], CFG_MAIN["y"]))
    
    pic2_bg = Image.open('pic2_bg.png').convert("RGBA")
    holo_img = Image.open('hologram.png').convert("RGBA")
    r, g, b, a = holo_img.split()
    a = a.point(lambda p: int(p * 0.45))
    holo_img.putalpha(a)
    
    manifest_data = []
    files = glob.glob(os.path.join(REVIEW_DS, '*.jpg'))
    
    for idx, f in enumerate(files):
        base = os.path.basename(f)
        print(f"[{idx+1}/{len(files)}] Processing {base}")
        main_p, ghost_p, reframes, detector = process_portrait(f)
        
        if main_p is None:
            print(" -> FAILED")
            continue
            
        card = template_img.copy()
        card.alpha_composite(main_p, (CFG_MAIN["x"], CFG_MAIN["y"]))
        card.alpha_composite(pic2_bg, (GHOST_BG_LEFT, GHOST_BG_TOP))
        card.alpha_composite(ghost_p, (CFG_GHOST["x"], CFG_GHOST["y"]))
        card.alpha_composite(holo_img, (HOLO_LEFT, HOLO_TOP))
        
        out_path = os.path.join(REVIEW_CARDS, f"card_{base}.png")
        card.convert("RGB").save(out_path, "PNG")
        
        manifest_data.append({
            "file_name": base,
            "detector_used": detector,
            "attempt_used": reframes,
            "crop_scale": "55%", # Fixed
            "reframed": False
        })
        
    with open(MANIFEST, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "detector_used", "attempt_used", "crop_scale", "reframed"])
        writer.writeheader()
        writer.writerows(manifest_data)
        
    print(f"Review Generation Complete! Wrote {len(manifest_data)} records.")

if __name__ == "__main__":
    main()
