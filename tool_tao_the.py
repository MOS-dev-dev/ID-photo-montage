import os
import sys
import io
import json
import random
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pandas as pd
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageChops
import mediapipe as mp

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DEBUG_MODE = True
DEBUG_DIR = "debug_output"
if DEBUG_MODE:
    os.makedirs(DEBUG_DIR, exist_ok=True)

# --- CONFIG ---
EXCEL_URL = "https://docs.google.com/spreadsheets/d/1qco4aN2TZoSHHEUMnxpl1_JAA8S2FXvTIkPI0gVadjA/export?format=csv&gid=1131043463"
TEMPLATE_PATH = "blank_template.png"
OUTPUT_DIR = "output_cards"

# Load JSON config
try:
    with open("template_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception as e:
    print(f"Lỗi đọc template_config.json: {e}")
    sys.exit(1)

CFG_MAIN = config["main_frame"]
CFG_GHOST = config["ghost_frame"]
MASK_BLUR = config["mask_blur_radius"]

# --- TEXT POSITIONS ---
ID_X = 509; ID_Y = 908
LAST_NAME_X = 1377; LAST_NAME_Y = 1063
FIRST_NAME_X = 1380; FIRST_NAME_Y = 1218
MIDDLE_NAME_X = 1374; MIDDLE_NAME_Y = 1438
DOB_X = 1377; DOB_Y = 1589
ADDRESS_X = 518; ADDRESS_Y = 1736
HOLO_LEFT = 876; HOLO_TOP = 1319
GHOST_BG_LEFT = 965; GHOST_BG_TOP = 1008

AVAILABLE_PHOTOS = {}

def get_random_face(target_gender, target_age, tolerance=20):
    gender_prefix = "anh_nam" if target_gender.upper() == "MALE" else "anh_nu"
    if target_age <= 35: age_suffix = "_tre"
    elif target_age <= 50: age_suffix = "_trung"
    else: age_suffix = "_gia"
        
    folder = f"{gender_prefix}{age_suffix}"
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    if folder not in AVAILABLE_PHOTOS or not AVAILABLE_PHOTOS[folder]:
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not files:
            print(f"  -> Lỗi: Thư mục {folder} đang TRỐNG!")
            return None
            
        AVAILABLE_PHOTOS[folder] = files
        random.shuffle(AVAILABLE_PHOTOS[folder])
        
    chosen = AVAILABLE_PHOTOS[folder].pop()
    print(f"   Lấy ảnh ({target_age} tuổi) từ thư mục {folder} -> {chosen} (còn lại {len(AVAILABLE_PHOTOS[folder])})")
    return os.path.join(folder, chosen)

def normalize_portrait(img_bgr):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl,a,b))
    final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return final

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. MediaPipe Face Landmarker
base_options = python.BaseOptions(model_asset_path='face_landmarker.task')
options = vision.FaceLandmarkerOptions(base_options=base_options,
                                       output_face_blendshapes=False,
                                       output_facial_transformation_matrixes=False,
                                       num_faces=1)
face_landmarker = vision.FaceLandmarker.create_from_options(options)

# 2. MediaPipe Face Detector
fd_base_options = python.BaseOptions(model_asset_path='blaze_face_short_range.tflite')
fd_options = vision.FaceDetectorOptions(base_options=fd_base_options, min_detection_confidence=0.5)
face_detector = vision.FaceDetector.create_from_options(fd_options)

# 3. OpenCV DNN Face Detector
cv_net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'res10_300x300_ssd_iter_140000.caffemodel')

def get_image_versions(img_bgr):
    versions = []
    versions.append(img_bgr) # A. Original
    
    # B. CLAHE
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(l)
    versions.append(cv2.cvtColor(cv2.merge((cl,a,b)), cv2.COLOR_LAB2BGR))
    
    # C. Brightness
    versions.append(cv2.convertScaleAbs(img_bgr, alpha=1.0, beta=30))
    
    # D. Contrast
    versions.append(cv2.convertScaleAbs(img_bgr, alpha=1.3, beta=0))
    
    # E. Sharpened
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    versions.append(cv2.filter2D(img_bgr, -1, kernel))
    
    return versions

def detect_face_multi_stage(original_bgr):
    versions = get_image_versions(original_bgr)
    
    for v_idx, img_bgr in enumerate(versions):
        h, w, _ = img_bgr.shape
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        
        # STAGE 1: Landmarker
        try:
            res_lm = face_landmarker.detect(mp_image)
            if res_lm and res_lm.face_landmarks:
                x_min, y_min = w, h
                x_max, y_max = 0, 0
                for lm in res_lm.face_landmarks[0]:
                    x, y = int(lm.x * w), int(lm.y * h)
                    x_min, y_min = min(x_min, x), min(y_min, y)
                    x_max, y_max = max(x_max, x), max(y_max, y)
                return {'x': x_min, 'y': y_min, 'w': x_max - x_min, 'h': y_max - y_min, 'detector': 'mediapipe_landmarker', 'version': v_idx}
        except: pass
        
        # STAGE 2: MP Detection
        try:
            res_fd = face_detector.detect(mp_image)
            if res_fd and res_fd.detections:
                bbox = res_fd.detections[0].bounding_box
                return {'x': bbox.origin_x, 'y': bbox.origin_y, 'w': bbox.width, 'h': bbox.height, 'detector': 'mediapipe_detection', 'version': v_idx}
        except: pass
        
        # STAGE 3: OpenCV DNN
        try:
            blob = cv2.dnn.blobFromImage(cv2.resize(img_bgr, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
            cv_net.setInput(blob)
            detections = cv_net.forward()
            best_conf = 0
            best_box = None
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > 0.5 and confidence > best_conf:
                    best_conf = confidence
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    best_box = {'x': startX, 'y': startY, 'w': endX - startX, 'h': endY - startY, 'detector': 'opencv_dnn', 'version': v_idx}
            if best_box:
                return best_box
        except: pass
        
    return None

def process_portrait(face_path, template_img=None, debug_id=None):
    img_array = np.fromfile(face_path, np.uint8)
    img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    # Normalize portrait
    img_bgr = normalize_portrait(img_bgr)
    
    face_img = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    
    try:
        from rembg import remove
        face_nobg = remove(face_img)
        a_arr = np.array(face_nobg.split()[3])
        if np.mean(a_arr) > 250 or np.mean(a_arr) < 5:
            raise Exception("Rembg mask error")
    except Exception as e:
        print(f"  -> Rembg fallback: {e}. Using MediaPipe Selfie Segmentation.")
        model_path = 'selfie_segmenter.tflite'
        if not os.path.exists(model_path):
            import urllib.request
            urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite', model_path)
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.ImageSegmenterOptions(base_options=base_options, output_confidence_masks=True)
        with vision.ImageSegmenter.create_from_options(options) as segmenter:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
            res = segmenter.segment(mp_image)
            mask = res.confidence_masks[1].numpy_view() if len(res.confidence_masks) > 1 else res.confidence_masks[0].numpy_view()
            alpha = (np.squeeze(mask) * 255).astype(np.uint8)
            
            # Ensure alpha shape matches image
            h, w = img_bgr.shape[:2]
            if alpha.shape != (h, w):
                alpha = cv2.resize(alpha, (w, h), interpolation=cv2.INTER_LINEAR)
                
            face_nobg = face_img.copy()
            face_nobg.putalpha(Image.fromarray(alpha))
        
    region = detect_face_multi_stage(img_bgr)
    if not region:
        print(f"  -> FAIL DETECT FACE (All 3 Detectors Exhausted)")
        return None, None, 0, None
        
    face_x, face_y, face_w, face_h = region['x'], region['y'], region['w'], region['h']
    
    target_w, target_h = CFG_MAIN["width"], CFG_MAIN["height"]
    target_ratio = target_w / target_h
    
    fw, fh = face_nobg.size
    
    # PORTRAIT-CROP SYSTEM
    # B1: Tỉ lệ chuẩn (khung rộng hơn để mặt nhỏ lại, lộ vai đều 2 bên)
    portrait_w = int(face_w * 4.2)
    portrait_h = int(portrait_w / target_ratio)
    
    eye_y = face_y + face_h * 0.45
    portrait_t = int(eye_y - 0.45 * portrait_h)
    portrait_b = portrait_t + portrait_h
    
    # B2: Tìm giới hạn dưới cùng thực sự của người (loại bỏ noise trong alpha)
    a_channel = np.array(face_nobg.split()[3])
    rows = np.any(a_channel > 50, axis=1)
    if np.any(rows):
        person_top, person_bottom = np.where(rows)[0][[0, -1]]
    else:
        person_top, person_bottom = 0, fh

    # B3: Đẩy khung hình lên trên để mép dưới khung vừa chạm mép dưới thân người (không lộ nền ở cổ)
    if portrait_b > person_bottom:
        shift_y = portrait_b - person_bottom
        portrait_b -= shift_y
        portrait_t -= shift_y
        
    # Nếu đẩy lên làm tràn luôn đỉnh đầu, bắt buộc phải thu nhỏ khung (zoom in) một chút
    if portrait_t < person_top:
        portrait_t = person_top
        portrait_h = portrait_b - portrait_t
        portrait_w = int(portrait_h * target_ratio)

    portrait_l = int(face_x + face_w / 2 - portrait_w / 2)
    portrait_r = portrait_l + portrait_w

    # B4: Tạo Canvas an toàn
    crop_canvas = Image.new('RGBA', (portrait_w, portrait_h), (255,255,255,0))
    
    src_l = max(0, portrait_l)
    src_t = max(0, portrait_t)
    src_r = min(fw, portrait_r)
    src_b = min(fh, portrait_b)
    
    if src_r > src_l and src_b > src_t:
        valid_crop = face_nobg.crop((src_l, src_t, src_r, src_b))
        paste_x = max(0, -portrait_l)
        paste_y = max(0, -portrait_t)
        crop_canvas.paste(valid_crop, (paste_x, paste_y))
        
    best_canvas = crop_canvas
    reframes = 1
    
    # Thu gọn lại (không ép giãn ngang nữa) để tránh bị tràn viền trái
    fit_img = ImageOps.fit(best_canvas, (target_w, target_h), method=Image.LANCZOS)
    
    if DEBUG_MODE and debug_id:
        fit_img.save(os.path.join(DEBUG_DIR, f"{debug_id}_02_fit.png"))
        


    
    # ==========================================
    # BACKGROUND ERASURE PATCH V2.1
    # ==========================================
    r, g, b, a = fit_img.split()
    rgb_arr = np.array(Image.merge('RGB', (r,g,b)))
    a_arr = np.array(a)
    
    if debug_id:
        os.makedirs('debug', exist_ok=True)
        fit_img.save(f"debug/{debug_id}_01_rembg_raw.png")
        a.save(f"debug/{debug_id}_02_alpha_before.png")
        
    # 2.1. ALPHA HARD SEPARATION
    hard_a = a_arr.copy()
    hard_a[a_arr < 40] = 0
    
    rgb_hard = rgb_arr.copy()
    rgb_hard[hard_a == 0] = 0
    
    if debug_id:
        Image.fromarray(np.dstack((rgb_hard, hard_a))).save(f"debug/{debug_id}_03_hard_cut.png")
        
    # 2.2. FOREGROUND COLOR RECONSTRUCTION (Premultiplied Blur)
    transition_mask = (a_arr >= 40) & (a_arr <= 220)
    
    a_float = a_arr.astype(np.float32) / 255.0
    p_float = rgb_arr.astype(np.float32) * a_float[:, :, None]
    
    pb = cv2.GaussianBlur(p_float, (31, 31), 0)
    ab = cv2.GaussianBlur(a_float, (31, 31), 0)
    ab[ab == 0] = 1.0 
    
    rgb_new = pb / ab[:, :, None]
    np.clip(rgb_new, 0, 255, out=rgb_new)
    rgb_new = rgb_new.astype(np.uint8)
    
    if debug_id:
        Image.fromarray(rgb_new).save(f"debug/{debug_id}_04_color_rebuild.png")
        
    # 2.3. EDGE DECONTAMINATION & COLOR SPILL REMOVAL (HSV Scan)
    kernel = np.ones((5,5), np.uint8)
    a_dilate = cv2.dilate(a_arr, kernel, iterations=1)
    edge_pixels = (a_dilate - a_arr) > 0
    
    rgb_arr[transition_mask] = rgb_new[transition_mask]
    
    R = rgb_arr[:, :, 0].astype(np.int32)
    G = rgb_arr[:, :, 1].astype(np.int32)
    B = rgb_arr[:, :, 2].astype(np.int32)
    
    blue_dom = B > (R * 1.2)
    gray_dom = (np.abs(R - G) < 10) & (np.abs(G - B) < 10)
    spill_mask = edge_pixels & (blue_dom | gray_dom)
    
    hard_a_float = hard_a.astype(np.float32)
    hard_a_float[spill_mask] *= 0.5
    hard_a = hard_a_float.astype(np.uint8)
    
    if debug_id:
        Image.fromarray(np.dstack((rgb_arr, hard_a))).save(f"debug/{debug_id}_05_edge_cleanup.png")
        
    # 2.4. ALPHA FEATHER
    edge_mask_for_blur = cv2.dilate(a_arr, np.ones((3,3), np.uint8), iterations=1) - cv2.erode(a_arr, np.ones((3,3), np.uint8), iterations=1)
    a_blurred = cv2.GaussianBlur(hard_a, (5, 5), 0)
    
    final_a = hard_a.copy()
    final_a[edge_mask_for_blur > 0] = a_blurred[edge_mask_for_blur > 0]
    
    a_arr = final_a
    
    if debug_id:
        Image.fromarray(np.dstack((rgb_arr, a_arr))).save(f"debug/{debug_id}_06_final_rgba.png")
    
    # 4. PORTRAIT COLOR MATCHING & LOCAL ADAPTATION
    local_bg_brightness = 0.5
    if template_img is not None:
        bg_patch = template_img.crop((CFG_MAIN["x"], CFG_MAIN["y"], CFG_MAIN["x"]+target_w, CFG_MAIN["y"]+target_h))
        bg_patch_lab = cv2.cvtColor(np.array(bg_patch.convert('RGB')), cv2.COLOR_RGB2LAB)
        tgt_l, tgt_a, tgt_b = cv2.split(bg_patch_lab)
        tgt_mean = [np.mean(tgt_l), np.mean(tgt_a), np.mean(tgt_b)]
        tgt_std = [np.std(tgt_l)+1e-5, np.std(tgt_a)+1e-5, np.std(tgt_b)+1e-5]
        
        local_bg_brightness = tgt_mean[0] / 255.0
        
        src_lab = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2LAB)
        src_l, src_a, src_b = cv2.split(src_lab)
        src_mean = [np.mean(src_l), np.mean(src_a), np.mean(src_b)]
        src_std = [np.std(src_l)+1e-5, np.std(src_a)+1e-5, np.std(src_b)+1e-5]
        
        res_l = np.clip((src_l - src_mean[0]) * (tgt_std[0] / src_std[0]) + tgt_mean[0], 0, 255).astype(np.uint8)
        res_a = np.clip((src_a - src_mean[1]) * (tgt_std[1] / src_std[1]) + tgt_mean[1], 0, 255).astype(np.uint8)
        res_b = np.clip((src_b - src_mean[2]) * (tgt_std[2] / src_std[2]) + tgt_mean[2], 0, 255).astype(np.uint8)
        
        matched_rgb = cv2.cvtColor(cv2.merge((res_l, res_a, res_b)), cv2.COLOR_LAB2RGB)
        rgb_arr = cv2.addWeighted(rgb_arr, 0.85, matched_rgb, 0.15, 0)
        
    rgb_img = Image.fromarray(rgb_arr)
    from PIL import ImageEnhance
    # Giảm mạnh độ sáng, độ tương phản và màu sắc để giống màu ảnh in trên thẻ gốc (tỉ lệ 1:1)
    rgb_img = ImageEnhance.Brightness(rgb_img).enhance(0.75)
    rgb_img = ImageEnhance.Contrast(rgb_img).enhance(0.85)
    rgb_img = ImageEnhance.Color(rgb_img).enhance(0.70)
    
    if debug_id:
        rgb_img.save(f"debug/{debug_id}_04_color_match.png")
    
    # 4.5 PORTRAIT DENSITY REDUCTION (Print-feel)
    rgb_arr_final = np.array(rgb_img)
    rgb_blur = cv2.GaussianBlur(rgb_arr_final, (3, 3), 0)
    rgb_arr_final = cv2.addWeighted(rgb_arr_final, 0.90, rgb_blur, 0.10, 0)
    rgb_img = Image.fromarray(rgb_arr_final)
    
    if debug_id:
        rgb_img.save(f"debug/{debug_id}_05_print_feel.png")
    
    # 5. HARD CUT + ROUNDED CORNERS (Bo góc để không bị tràn sắc cạnh ra ngoài khung xám)
    final_a = Image.fromarray(a_arr)
    
    corner_radius = 25
    mask = Image.new('L', (target_w, target_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, target_w, target_h], radius=corner_radius, fill=255)
    
    final_a = ImageChops.multiply(final_a, mask)
    
    # 6. MAIN PORTRAIT: Apply the final alpha mask (transparent background)
    main_portrait = rgb_img.convert("RGBA")
    main_portrait.putalpha(final_a)
    
    if debug_id:
        main_portrait.save(f"debug/{debug_id}_06_final_main.png")
    
    # 7. GHOST SYNCHRONIZATION (from the faded portrait)
    ghost_w, ghost_h = CFG_GHOST["width"], CFG_GHOST["height"]
    ghost_raw = main_portrait.resize((ghost_w, ghost_h), Image.LANCZOS)
    
    r_g, g_g, b_g, a_g = ghost_raw.split()
    gray_g = Image.merge('RGB', (r_g, g_g, b_g)).convert('L').convert('RGB')
    
    # Make ghost very faint (about 25% opacity) to match reference
    a_g = a_g.point(lambda p: int(p * 0.25))
    
    ghost_portrait = gray_g.convert("RGBA")
    ghost_portrait.putalpha(a_g)
    
    if debug_id:
        ghost_portrait.save(f"debug/{debug_id}_07_final_ghost.png")
    
    # 8. QUALITY CHECK (halo detection)
    kernel_dilate = np.ones((5,5), np.uint8)
    a_dilate = cv2.dilate(a_arr, kernel_dilate, iterations=1)
    a_erode = cv2.erode(a_arr, kernel_dilate, iterations=1)
    edge_zone = a_dilate - a_erode
    
    hsv = cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2HSV)
    h_c, s_c, v_c = cv2.split(hsv)
    blue_green_mask = ((h_c > 40) & (h_c < 140) & (s_c > 40))
    halo_pixels = (blue_green_mask & (edge_zone > 0)).sum()
    total_edge_pixels = (edge_zone > 0).sum()
    
    if total_edge_pixels > 0:
        halo_ratio = halo_pixels / total_edge_pixels
        if halo_ratio > 0.05:
            print(f"  -> WARNING: Phát hiện viền xanh (Halo ratio {halo_ratio*100:.1f}%), nhưng vẫn tiếp tục tạo ảnh.")
            # Bỏ qua việc chặn lỗi, cứ tạo thẻ bình thường
            # return None, None, 0, "halo_detected"
            
    return main_portrait, ghost_portrait, reframes, region.get('detector')

def make_id_card(row, template_img, font_id, font_name, font_dob, font_reg, pic2_bg, holo_img, debug_counter=None):
    id_num = str(row['ID_NUM']).strip()
    last_name = str(row['LAST_NAME']).strip()
    first_name = str(row['FIRST_NAME']).strip()
    middle_name = str(row['MIDDLE_NAME']).strip()
    dob = str(row['DOB']).strip()
    address = str(row['ADDRESS']).strip()
    gender = str(row['GENDER']).strip()
    
    try: target_age = 2026 - int(dob.split(",")[-1].strip())
    except: target_age = 30
    
    print(f"\n{'='*50}\n {first_name} {last_name} ({gender}, {target_age}t)\n{'='*50}")
    
    face_path = get_random_face(gender, target_age)
    if not face_path:
        return
        
    debug_id = f"debug_{debug_counter:03d}" if debug_counter is not None else None
    result = process_portrait(face_path, template_img=template_img, debug_id=debug_id)
    if result is not None and len(result) == 4:
        main_portrait, ghost_portrait, reframes, detector_used = result
    else:
        main_portrait = None
        
    if not main_portrait:
        print("  -> SKIPPED record due to detector/blending failure.")
        return
        
    print(f"  -> Adaptive Reframing: Used attempt #{reframes}")
    
    card = template_img.copy()
    
    card.alpha_composite(main_portrait, (CFG_MAIN["x"], CFG_MAIN["y"]))
    card.alpha_composite(pic2_bg, (GHOST_BG_LEFT, GHOST_BG_TOP))
    card.alpha_composite(ghost_portrait, (CFG_GHOST["x"], CFG_GHOST["y"]))
    card.alpha_composite(holo_img, (HOLO_LEFT, HOLO_TOP))
    
    if debug_id:
        card.convert("RGB").save(f"debug/{debug_id}_07_composite.png")
        
    draw = ImageDraw.Draw(card)
    text_color = (0, 0, 0)
    
    draw.text((ID_X, ID_Y), id_num, font=font_id, fill=text_color)
    draw.text((LAST_NAME_X, LAST_NAME_Y), last_name, font=font_name, fill=text_color)
    draw.text((FIRST_NAME_X, FIRST_NAME_Y), first_name, font=font_name, fill=text_color)
    draw.text((MIDDLE_NAME_X, MIDDLE_NAME_Y), middle_name, font=font_name, fill=text_color)
    draw.text((DOB_X, DOB_Y), dob, font=font_dob, fill=text_color)
    
    # Làm nhạt phần địa chỉ (Address) bằng cách giảm Opacity (màu đen trong suốt)
    # Giảm xuống 100 để chữ mờ và nhạt hẳn đi giống ảnh mẫu
    address_color = (0, 0, 0, 100) 
    draw.text((ADDRESS_X, ADDRESS_Y), address, font=font_reg, fill=address_color)
    
    out_name = f"{last_name}.{first_name}.{middle_name}"
    
    # Tìm số thư mục tiếp theo (1, 2, 3...)
    existing_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and d.isdigit()]
    next_num = max([int(d) for d in existing_dirs]) + 1 if existing_dirs else 1
    out_folder = str(next_num)
    os.makedirs(out_folder, exist_ok=True)
    
    # Lưu thẻ thành phẩm (.png)
    img_path = os.path.join(out_folder, f"{out_name}.png")
    card.convert("RGB").save(img_path, "PNG")
    
    # Lưu file text chứa thông tin (.txt)
    txt_path = os.path.join(out_folder, f"{id_num}.txt")
    row_text = "\t".join(row.fillna('').astype(str).tolist())
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(row_text)
        
    print(f"  -> SAVED: Thư mục {out_folder} (chứa PNG và TXT)")
    
    if os.path.exists(face_path) and "test_tpdne" not in face_path and "pinterest_face" not in face_path:
        os.remove(face_path)

def run_generation(start_idx, end_idx, log_fn, progress_fn, done_fn):
    """Worker function that runs in a background thread."""
    try:
        log_fn("[SETUP] Đang tải template và tài nguyên...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        template_img = Image.open(TEMPLATE_PATH).convert("RGBA")

        pic2_bg = Image.open('pic2_bg.png').convert("RGBA")
        holo_img = Image.open('hologram.png').convert("RGBA")

        # Làm mờ cánh hoa (hologram) và giảm nhạt đi
        holo_img = holo_img.filter(ImageFilter.GaussianBlur(1))
        r, g, b, a = holo_img.split()
        a = a.point(lambda p: int(p * 0.25))
        holo_img.putalpha(a)

        # Đã canh chỉnh tỉ lệ 1:1 (replica) với phông chữ gốc của thẻ thật
        # Tỉ lệ chính xác 100% theo PT size từ Photoshop
        font_id = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 70)
        font_name = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 70)
        font_dob = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 74)
        font_reg = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 61)

        log_fn("[SETUP] Đang tải dữ liệu từ Google Sheets...")
        try:
            df = pd.read_csv(EXCEL_URL, header=None, names=['ID_NUM','LAST_NAME','FIRST_NAME','MIDDLE_NAME','DOB','ADDRESS','GENDER','PLACE_OF_BIRTH', 'C9','C10','C11','C12','C13','C14','C15','C16','C17'])
        except Exception as e:
            log_fn(f"[LỖI] Không tải được dữ liệu: {e}")
            done_fn(False)
            return

        if start_idx < 0:
            start_idx_safe = 0
        else:
            start_idx_safe = start_idx
        if end_idx > len(df):
            end_idx_safe = len(df)
        else:
            end_idx_safe = end_idx

        total = end_idx_safe - start_idx_safe
        if total <= 0:
            log_fn("[LỖI] Khoảng dòng không hợp lệ!")
            done_fn(False)
            return

        log_fn(f"[START] Bắt đầu tạo thẻ từ dòng {start_idx_safe + 1} đến {end_idx_safe} ({total} thẻ)")
        log_fn("=" * 50)

        debug_counter = 1
        completed = 0
        for _, row in df.iloc[start_idx_safe:end_idx_safe].iterrows():
            try:
                if debug_counter <= 20:
                    make_id_card(row, template_img, font_id, font_name, font_dob, font_reg, pic2_bg, holo_img, debug_counter=debug_counter)
                else:
                    make_id_card(row, template_img, font_id, font_name, font_dob, font_reg, pic2_bg, holo_img)
                debug_counter += 1
            except Exception as e:
                log_fn(f"[LỖI] {e}")
            completed += 1
            progress_fn(completed / total)

        log_fn("=" * 50)
        log_fn(f"[XONG] Hoàn thành! Đã xử lý {completed}/{total} thẻ.")
        log_fn(f"[XONG] Kết quả lưu tại: {os.path.abspath(OUTPUT_DIR)}")
        done_fn(True)
    except Exception as e:
        log_fn(f"[LỖI NGHIÊM TRỌNG] {e}")
        done_fn(False)


class ToolTaoTheGUI:
    # Color palette
    BG_DARK = "#1a1a2e"
    BG_CARD = "#16213e"
    BG_INPUT = "#0f3460"
    BG_LOG = "#0a0a1a"
    FG_TEXT = "#e0e0e0"
    FG_DIM = "#8a8a9a"
    FG_ACCENT = "#00d2ff"
    FG_SUCCESS = "#00e676"
    FG_ERROR = "#ff5252"
    FG_WARN = "#ffc107"
    BTN_BG = "#e94560"
    BTN_HOVER = "#ff6b81"
    BTN_DISABLED = "#444466"
    BORDER_COLOR = "#2a2a4a"

    def __init__(self, root):
        self.root = root
        self.root.title("Tool Tạo Thẻ Căn Cước Tự Động")
        self.root.configure(bg=self.BG_DARK)
        self.root.resizable(True, True)
        self.root.minsize(750, 600)

        # Center window
        w, h = 800, 680
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.msg_queue = queue.Queue()
        self.is_running = False

        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        # --- HEADER ---
        header_frame = tk.Frame(self.root, bg=self.BG_DARK, pady=15)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(header_frame, text="🪪  TOOL TẠO THẺ CĂN CƯỚC",
                             font=("Segoe UI", 20, "bold"), fg=self.FG_ACCENT, bg=self.BG_DARK)
        title_lbl.pack()

        sub_lbl = tk.Label(header_frame, text="Tự động tạo thẻ căn cước từ dữ liệu Google Sheets",
                           font=("Segoe UI", 10), fg=self.FG_DIM, bg=self.BG_DARK)
        sub_lbl.pack(pady=(2, 0))

        # --- SEPARATOR ---
        sep = tk.Frame(self.root, bg=self.FG_ACCENT, height=1)
        sep.pack(fill=tk.X, padx=30)

        # --- INPUT CARD ---
        card_frame = tk.Frame(self.root, bg=self.BG_CARD, bd=0, highlightthickness=1,
                              highlightbackground=self.BORDER_COLOR)
        card_frame.pack(fill=tk.X, padx=30, pady=15)

        inner = tk.Frame(card_frame, bg=self.BG_CARD, padx=20, pady=15)
        inner.pack(fill=tk.X)

        # Row inputs
        row_frame = tk.Frame(inner, bg=self.BG_CARD)
        row_frame.pack(fill=tk.X)

        # Start row
        start_group = tk.Frame(row_frame, bg=self.BG_CARD)
        start_group.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))

        tk.Label(start_group, text="📍 Dòng Bắt Đầu", font=("Segoe UI", 10, "bold"),
                 fg=self.FG_TEXT, bg=self.BG_CARD).pack(anchor=tk.W)
        self.start_entry = tk.Entry(start_group, font=("Segoe UI", 14), bg=self.BG_INPUT,
                                    fg="#ffffff", insertbackground="#ffffff",
                                    relief=tk.FLAT, bd=0, highlightthickness=1,
                                    highlightcolor=self.FG_ACCENT, highlightbackground=self.BORDER_COLOR)
        self.start_entry.pack(fill=tk.X, ipady=6, pady=(4, 0))
        self.start_entry.insert(0, "2160")

        # End row
        end_group = tk.Frame(row_frame, bg=self.BG_CARD)
        end_group.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(10, 0))

        tk.Label(end_group, text="🏁 Dòng Kết Thúc", font=("Segoe UI", 10, "bold"),
                 fg=self.FG_TEXT, bg=self.BG_CARD).pack(anchor=tk.W)
        self.end_entry = tk.Entry(end_group, font=("Segoe UI", 14), bg=self.BG_INPUT,
                                  fg="#ffffff", insertbackground="#ffffff",
                                  relief=tk.FLAT, bd=0, highlightthickness=1,
                                  highlightcolor=self.FG_ACCENT, highlightbackground=self.BORDER_COLOR)
        self.end_entry.pack(fill=tk.X, ipady=6, pady=(4, 0))
        self.end_entry.insert(0, "2170")

        # Button row
        btn_frame = tk.Frame(inner, bg=self.BG_CARD, pady=12)
        btn_frame.pack(fill=tk.X)

        self.run_btn = tk.Button(btn_frame, text="▶  BẮT ĐẦU TẠO THẺ",
                                 font=("Segoe UI", 12, "bold"), bg=self.BTN_BG, fg="#ffffff",
                                 activebackground=self.BTN_HOVER, activeforeground="#ffffff",
                                 relief=tk.FLAT, cursor="hand2", bd=0, padx=30, pady=8,
                                 command=self._on_start)
        self.run_btn.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(btn_frame, text="⏸ Sẵn sàng",
                                   font=("Segoe UI", 10), fg=self.FG_DIM, bg=self.BG_CARD)
        self.status_lbl.pack(side=tk.LEFT, padx=15)

        # Hover effects
        self.run_btn.bind("<Enter>", lambda e: self.run_btn.configure(bg=self.BTN_HOVER) if not self.is_running else None)
        self.run_btn.bind("<Leave>", lambda e: self.run_btn.configure(bg=self.BTN_BG) if not self.is_running else None)

        # --- PROGRESS BAR ---
        prog_frame = tk.Frame(self.root, bg=self.BG_DARK, padx=30)
        prog_frame.pack(fill=tk.X)

        self.progress_var = tk.DoubleVar(value=0)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=self.BG_CARD,
                        background=self.FG_ACCENT,
                        bordercolor=self.BORDER_COLOR,
                        lightcolor=self.FG_ACCENT,
                        darkcolor=self.FG_ACCENT,
                        thickness=6)
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var,
                                            maximum=100, style="Custom.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.progress_lbl = tk.Label(prog_frame, text="", font=("Segoe UI", 9),
                                     fg=self.FG_DIM, bg=self.BG_DARK, anchor=tk.E)
        self.progress_lbl.pack(fill=tk.X)

        # --- LOG CONSOLE ---
        log_header = tk.Frame(self.root, bg=self.BG_DARK, padx=30)
        log_header.pack(fill=tk.X, pady=(5, 0))
        tk.Label(log_header, text="📋 Log Console", font=("Segoe UI", 10, "bold"),
                 fg=self.FG_DIM, bg=self.BG_DARK).pack(anchor=tk.W)

        log_frame = tk.Frame(self.root, bg=self.BG_LOG, bd=0, highlightthickness=1,
                             highlightbackground=self.BORDER_COLOR, padx=30)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(4, 15))

        self.log_text = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9),
                                                   bg=self.BG_LOG, fg=self.FG_TEXT,
                                                   insertbackground=self.FG_TEXT,
                                                   relief=tk.FLAT, bd=0,
                                                   wrap=tk.WORD, state=tk.DISABLED,
                                                   selectbackground=self.BG_INPUT)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tag colors for log
        self.log_text.tag_configure("info", foreground=self.FG_TEXT)
        self.log_text.tag_configure("success", foreground=self.FG_SUCCESS)
        self.log_text.tag_configure("error", foreground=self.FG_ERROR)
        self.log_text.tag_configure("warn", foreground=self.FG_WARN)
        self.log_text.tag_configure("accent", foreground=self.FG_ACCENT)

    def _log(self, msg):
        """Thread-safe log: push message to queue."""
        self.msg_queue.put(("log", msg))

    def _update_progress(self, fraction):
        """Thread-safe progress update."""
        self.msg_queue.put(("progress", fraction))

    def _done(self, success):
        """Thread-safe done signal."""
        self.msg_queue.put(("done", success))

    def _poll_queue(self):
        """Check the message queue from the main thread and update UI."""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self._append_log(data)
                elif msg_type == "progress":
                    pct = data * 100
                    self.progress_var.set(pct)
                    self.progress_lbl.config(text=f"{pct:.0f}%")
                elif msg_type == "done":
                    self.is_running = False
                    self.run_btn.config(state=tk.NORMAL, bg=self.BTN_BG, text="▶  BẮT ĐẦU TẠO THẺ")
                    self.start_entry.config(state=tk.NORMAL)
                    self.end_entry.config(state=tk.NORMAL)
                    if data:
                        self.status_lbl.config(text="✅ Hoàn thành!", fg=self.FG_SUCCESS)
                    else:
                        self.status_lbl.config(text="❌ Có lỗi xảy ra", fg=self.FG_ERROR)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _append_log(self, text):
        """Append a line to the log console with color tags."""
        self.log_text.config(state=tk.NORMAL)

        # Determine tag based on content
        tag = "info"
        if "[LỖI]" in text or "[LỖI NGHIÊM TRỌNG]" in text or "FAIL" in text or "LOI:" in text:
            tag = "error"
        elif "[XONG]" in text or "SAVED:" in text:
            tag = "success"
        elif "[SETUP]" in text or "[START]" in text:
            tag = "accent"
        elif "WARNING" in text or "SKIPPED" in text:
            tag = "warn"

        self.log_text.insert(tk.END, text + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _on_start(self):
        if self.is_running:
            return

        start_str = self.start_entry.get().strip()
        end_str = self.end_entry.get().strip()

        try:
            start_idx = int(start_str) - 1
            end_idx = int(end_str)
        except ValueError:
            messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ cho dòng bắt đầu và kết thúc!")
            return

        if end_idx <= start_idx:
            messagebox.showerror("Lỗi", "Dòng kết thúc phải lớn hơn dòng bắt đầu!")
            return

        # Clear log and progress
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_lbl.config(text="")

        # Lock UI
        self.is_running = True
        self.run_btn.config(state=tk.DISABLED, bg=self.BTN_DISABLED, text="⏳ Đang xử lý...")
        self.start_entry.config(state=tk.DISABLED)
        self.end_entry.config(state=tk.DISABLED)
        self.status_lbl.config(text="⚙ Đang tạo thẻ...", fg=self.FG_ACCENT)

        # Redirect print to GUI log
        class PrintRedirector(io.TextIOBase):
            def __init__(self, log_fn):
                self._log = log_fn
            def write(self, text):
                if text and text.strip():
                    self._log(text.rstrip())
                return len(text) if text else 0
            def flush(self):
                pass

        sys.stdout = PrintRedirector(self._log)

        # Launch worker thread
        worker = threading.Thread(target=run_generation,
                                  args=(start_idx, end_idx, self._log, self._update_progress, self._done),
                                  daemon=True)
        worker.start()


def main():
    root = tk.Tk()
    app = ToolTaoTheGUI(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    finally:
        # Explicitly close MediaPipe objects to prevent cleanup errors on exit
        if 'face_landmarker' in globals():
            face_landmarker.close()
        if 'face_detector' in globals():
            face_detector.close()