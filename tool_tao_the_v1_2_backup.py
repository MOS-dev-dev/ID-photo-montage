import os
import sys
import io
import json
import random
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
    # B1: Từ face box tạo portrait box (Bao gồm tóc, đầu, cổ, vai)
    # Tỷ lệ: Face Width chiếm khoảng 50% khung hình
    portrait_w = int(face_w * 2.0)
    portrait_h = int(portrait_w / target_ratio)
    
    # Định vị tọa độ mắt
    eye_y = face_y + face_h * 0.45
    
    # Kéo dài portrait box lên trên (lấy tóc) và xuống dưới (lấy cổ, vai)
    # Sao cho Eye Y luôn nằm ở mốc 40% của khung
    portrait_t = int(eye_y - 0.40 * portrait_h)
    portrait_l = int(face_x + face_w / 2 - portrait_w / 2)
    portrait_r = portrait_l + portrait_w
    portrait_b = portrait_t + portrait_h
    
    # B2: Tạo Canvas an toàn (tránh tràn viền)
    crop_canvas = Image.new('RGBA', (portrait_w, portrait_h), (0,0,0,0))
    
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
    reframes = 1 # Chỉ cần 1 lần crop là chuẩn xác
    
    if DEBUG_MODE and debug_id:
        best_canvas.save(os.path.join(DEBUG_DIR, f"{debug_id}_01_crop.png"))

    fit_img = ImageOps.fit(best_canvas, (target_w, target_h), method=Image.LANCZOS)
    if DEBUG_MODE and debug_id:
        fit_img.save(os.path.join(DEBUG_DIR, f"{debug_id}_02_fit.png"))
        
    mask = Image.new("L", (target_w, target_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    inset = MASK_BLUR
    mask_draw.rectangle([inset, inset, target_w - inset, target_h - inset], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(MASK_BLUR))
    
    # ==========================================
    # BACKGROUND BLENDING SYSTEM V1.2
    # ==========================================
    r, g, b, a = fit_img.split()
    rgb_arr = np.array(Image.merge('RGB', (r,g,b)))
    a_arr = np.array(a)
    
    if debug_id:
        os.makedirs('debug', exist_ok=True)
        fit_img.save(f"debug/{debug_id}_01_original.png")
        a.save(f"debug/{debug_id}_02_alpha_mask.png")
    
    # 2. EDGE CLEANUP
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    a_arr = cv2.morphologyEx(a_arr, cv2.MORPH_CLOSE, kernel)
    a_arr = cv2.GaussianBlur(a_arr, (7, 7), 0)
    
    # 3. COLOR DECONTAMINATION (Khử Halo xịn bằng Premultiplied Blur)
    fg_only = rgb_arr.copy()
    fg_only[a_arr < 220] = 0
    mask_float = (a_arr >= 220).astype(np.float32)
    fg_float = fg_only.astype(np.float32)
    
    blur_mask = cv2.GaussianBlur(mask_float, (31, 31), 0)
    blur_fg = cv2.GaussianBlur(fg_float, (31, 31), 0)
    blur_mask[blur_mask == 0] = 1.0 # avoid div zero
    
    decontaminated_rgb = (blur_fg / blur_mask[:, :, None])
    np.clip(decontaminated_rgb, 0, 255, out=decontaminated_rgb)
    decontaminated_rgb = decontaminated_rgb.astype(np.uint8)
    
    edge_mask = ((a_arr > 20) & (a_arr < 220))
    rgb_arr[edge_mask] = decontaminated_rgb[edge_mask]
    
    if debug_id:
        Image.fromarray(rgb_arr).save(f"debug/{debug_id}_03_decontamination.png")
    
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
    rgb_img = ImageEnhance.Brightness(rgb_img).enhance(0.85)
    rgb_img = ImageEnhance.Contrast(rgb_img).enhance(0.90)
    rgb_img = ImageEnhance.Color(rgb_img).enhance(0.80)
    
    if debug_id:
        rgb_img.save(f"debug/{debug_id}_04_color_match.png")
    
    # 4.5 PORTRAIT DENSITY REDUCTION (Print-feel)
    rgb_arr_final = np.array(rgb_img)
    rgb_blur = cv2.GaussianBlur(rgb_arr_final, (3, 3), 0)
    rgb_arr_final = cv2.addWeighted(rgb_arr_final, 0.90, rgb_blur, 0.10, 0)
    rgb_img = Image.fromarray(rgb_arr_final)
    
    if debug_id:
        rgb_img.save(f"debug/{debug_id}_05_print_feel.png")
    
    # 5. SOFT BODY BLEND
    fade_mask = Image.new('L', (target_w, target_h), 255)
    draw = ImageDraw.Draw(fade_mask)
    h50 = int(target_h * 0.50)
    h65 = int(target_h * 0.65)
    h80 = int(target_h * 0.80)
    
    draw.rectangle([0, h50, target_w, h65], fill=242)
    draw.rectangle([0, h65, target_w, h80], fill=216)
    
    grad_height = target_h - h80
    if grad_height > 0:
        grad = Image.new('L', (1, grad_height))
        for y in range(grad_height):
            val = int(178 - (51 * y / grad_height))
            grad.putpixel((0, y), val)
        grad = grad.resize((target_w, grad_height))
        fade_mask.paste(grad, (0, h80))
        
    fade_mask = fade_mask.filter(ImageFilter.GaussianBlur(15))
    final_a = ImageChops.multiply(Image.fromarray(a_arr), fade_mask)
    final_a = final_a.point(lambda p: 0 if p < 15 else p)
    
    # Kẹp thêm mask bo viền của template
    final_a = ImageChops.multiply(final_a, mask)
    
    # Feather Alpha Edge Integration (Làm mềm viền 3px)
    final_a = final_a.filter(ImageFilter.GaussianBlur(3))
    
    main_portrait = rgb_img.convert("RGBA")
    main_portrait.putalpha(final_a)
    
    if debug_id:
        main_portrait.save(f"debug/{debug_id}_06_final_main.png")
    
    # 7. GHOST SYNCHRONIZATION PLUS
    ghost_w, ghost_h = CFG_GHOST["width"], CFG_GHOST["height"]
    ghost_portrait_raw = main_portrait.resize((ghost_w, ghost_h), Image.LANCZOS)
    
    r_g, g_g, b_g, a_g = ghost_portrait_raw.split()
    gray_g = Image.merge('RGB', (r_g, g_g, b_g)).convert('L').convert('RGB')
    a_g = a_g.point(lambda p: int(p * 0.31))
    
    ghost_portrait = gray_g.convert("RGBA")
    ghost_portrait.putalpha(a_g)
    
    if debug_id:
        ghost_portrait.save(f"debug/{debug_id}_07_final_ghost.png")
    
    # 8. FINAL QUALITY CHECK
    kernel_dilate = np.ones((5,5), np.uint8)
    a_dilate = cv2.dilate(np.array(final_a), kernel_dilate, iterations=1)
    a_erode = cv2.erode(np.array(final_a), kernel_dilate, iterations=1)
    edge_zone = a_dilate - a_erode
    
    hsv = cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2HSV)
    h_c, s_c, v_c = cv2.split(hsv)
    blue_green_mask = ((h_c > 40) & (h_c < 140) & (s_c > 40))
    halo_pixels = (blue_green_mask & (edge_zone > 0)).sum()
    total_edge_pixels = (edge_zone > 0).sum()
    
    if total_edge_pixels > 0:
        halo_ratio = halo_pixels / total_edge_pixels
        if halo_ratio > 0.05:
            print(f"  -> FAIL BLENDING: Halo xanh tỷ lệ {halo_ratio*100:.1f}%")
            return None, None, 0, "halo_detected"
            
    return main_portrait, ghost_portrait, reframes, region.get('detector')

def make_id_card(row, template_img, font_id, font_bold, font_reg, pic2_bg, holo_img, debug_counter=None):
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
        card.convert("RGB").save(f"debug/{debug_id}_08_final_card.png")
        
    draw = ImageDraw.Draw(card)
    text_color = (0, 0, 0)
    
    draw.text((ID_X, ID_Y), id_num, font=font_id, fill=text_color)
    draw.text((LAST_NAME_X, LAST_NAME_Y), last_name, font=font_bold, fill=text_color)
    draw.text((FIRST_NAME_X, FIRST_NAME_Y), first_name, font=font_bold, fill=text_color)
    draw.text((MIDDLE_NAME_X, MIDDLE_NAME_Y), middle_name, font=font_bold, fill=text_color)
    draw.text((DOB_X, DOB_Y), dob, font=font_bold, fill=text_color)
    draw.text((ADDRESS_X, ADDRESS_Y), address, font=font_reg, fill=text_color)
    
    out_name = f"{last_name}.{first_name}.{middle_name}"
    img_path = os.path.join(OUTPUT_DIR, f"{out_name}.png")
    card.convert("RGB").save(img_path, "PNG")
    print(f"  -> SAVED: {img_path}")
    
    if os.path.exists(face_path) and "test_tpdne" not in face_path and "pinterest_face" not in face_path:
        os.remove(face_path)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
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
    
    font_id = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 65)
    font_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 60)
    font_reg = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 50)
    
    try:
        df = pd.read_csv(EXCEL_URL, header=None, names=['ID_NUM','LAST_NAME','FIRST_NAME','MIDDLE_NAME','DOB','ADDRESS','GENDER','PLACE_OF_BIRTH', 'C9','C10','C11','C12','C13','C14','C15','C16','C17'])
    except Exception as e:
        print(f"Loi: {e}")
        return
    
    print("\n" + "="*50)
    start_row = input("Nhập dòng BẮT ĐẦU trong file Excel (VD: 2160): ").strip()
    end_row = input("Nhập dòng KẾT THÚC trong file Excel (VD: 2170): ").strip()
    print("="*50 + "\n")
    
    try:
        start_idx = int(start_row) - 1
        end_idx = int(end_row)
    except:
        print("Lỗi: Vui lòng nhập số hợp lệ!")
        return

    if start_idx < 0: start_idx = 0
    if end_idx > len(df): end_idx = len(df)
    
    print(f"*** BẮT ĐẦU TẠO THẺ TỪ DÒNG {start_row} ĐẾN {end_row} ***")
    debug_counter = 1
    for _, row in df.iloc[start_idx:end_idx].iterrows():
        try:
            if debug_counter <= 20:
                make_id_card(row, template_img, font_id, font_bold, font_reg, pic2_bg, holo_img, debug_counter=debug_counter)
            else:
                make_id_card(row, template_img, font_id, font_bold, font_reg, pic2_bg, holo_img)
            debug_counter += 1
        except Exception as e:
            print(f"LOI: {e}")

if __name__ == "__main__":
    main()