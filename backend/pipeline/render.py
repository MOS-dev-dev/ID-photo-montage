import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageDraw, ImageChops
import os
import json

def map_frame(preview_frame, target_w, target_h):
    """
    Maps preview frame coordinates to template resolution.
    preview_frame is the json object from frontend.
    """
    saved_x = preview_frame.get("x", 0)
    saved_y = preview_frame.get("y", 0)
    saved_scale = preview_frame.get("scale", 1.0)
    
    preview_w = preview_frame.get("canvas_width", 490)
    preview_h = preview_frame.get("canvas_height", 650)
    
    ratio_x = target_w / preview_w
    ratio_y = target_h / preview_h
    
    real_x = saved_x * ratio_x
    real_y = saved_y * ratio_y
    real_scale = saved_scale * ratio_x
    
    return {
        "x": real_x,
        "y": real_y,
        "scale": real_scale,
        "rotation": preview_frame.get("rotation", 0),
        "width": preview_frame.get("width", 0) * ratio_x,
        "height": preview_frame.get("height", 0) * ratio_y,
        "canvas_width": target_w,
        "canvas_height": target_h
    }

def apply_body_fade(alpha_arr):
    """
    Applies a vertical gradient fade at the bottom of the mask.
    Fades from 100% to 85% opacity over the bottom 15% of the image.
    """
    h, w = alpha_arr.shape
    fade_height = int(h * 0.15)
    fade_start_y = h - fade_height
    
    gradient = np.linspace(1.0, 0.85, fade_height)
    gradient_2d = np.tile(gradient[:, np.newaxis], (1, w))
    
    alpha_float = alpha_arr.astype(np.float32)
    alpha_float[fade_start_y:h, :] = alpha_float[fade_start_y:h, :] * gradient_2d
    
    return alpha_float.astype(np.uint8)

def render_final_card(framed_canvas, template_img, config, image_adjust, 
                      pic2_bg=None, holo_img=None, text_data=None, fonts=None, is_preview=False):
    """
    Applies V2.1 Erasure, adjustments, and composites the final card.
    """
    target_w, target_h = config["main_frame"]["width"], config["main_frame"]["height"]
    
    # ==========================================
    # INITIALIZE RGB & ALPHA & STAGE A
    # ==========================================
    r, g, b, a = framed_canvas.split()
    rgb_img = Image.merge('RGB', (r,g,b))
    rgb_img = rgb_img.convert('RGB')
    
    # Custom Adjustments from UI
    raw_brightness = image_adjust.get("brightness", 1.0)
    raw_contrast = image_adjust.get("contrast", 1.0)
    raw_saturation = image_adjust.get("saturation", 1.0)
    
    brightness = 1 + (raw_brightness - 1) * 2.0
    contrast   = 1 + (raw_contrast - 1) * 2.0
    saturation = 1 + (raw_saturation - 1) * 2.5
    
    # STAGE A: 50% strength before mask
    brightness_A = 1 + (brightness - 1) * 0.5
    contrast_A = 1 + (contrast - 1) * 0.5
    saturation_A = 1 + (saturation - 1) * 0.5
    
    rgb_img = ImageEnhance.Brightness(rgb_img).enhance(brightness_A)
    rgb_img = ImageEnhance.Contrast(rgb_img).enhance(contrast_A)
    rgb_img = ImageEnhance.Color(rgb_img).enhance(saturation_A)
    
    rgb_arr = np.array(rgb_img)
    a_arr = np.array(a)
    
    # ==========================================
    # BACKGROUND ERASURE PATCH V2.1 (STEP 4)
    # ==========================================
    # 2.1. ALPHA HARD SEPARATION
    hard_a = a_arr.copy()
    hard_a[a_arr < 40] = 0
    
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
    
    # 2.4. ALPHA FEATHER
    edge_mask_for_blur = cv2.dilate(a_arr, np.ones((3,3), np.uint8), iterations=1) - cv2.erode(a_arr, np.ones((3,3), np.uint8), iterations=1)
    a_blurred = cv2.GaussianBlur(hard_a, (5, 5), 0)
    
    final_a_arr = hard_a.copy()
    final_a_arr[edge_mask_for_blur > 0] = a_blurred[edge_mask_for_blur > 0]
    
    # ==========================================
    # OUTPUT QUALITY FIXES
    # ==========================================
    # Print-feel Blur (Reduced from 10% to 3%)
    rgb_arr_final = rgb_arr.copy()
    rgb_blur = cv2.GaussianBlur(rgb_arr_final, (3, 3), 0)
    rgb_arr_final = cv2.addWeighted(rgb_arr_final, 0.97, rgb_blur, 0.03, 0)
    rgb_img = Image.fromarray(rgb_arr_final)
    
    # Body Fade (100 -> 85)
    final_a_arr = apply_body_fade(final_a_arr)
    
    # HARD CUT + ROUNDED CORNERS
    final_a = Image.fromarray(final_a_arr)
    corner_radius = 25
    mask = Image.new('L', (target_w, target_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, target_w, target_h], radius=corner_radius, fill=255)
    
    final_a = ImageChops.multiply(final_a, mask)
    
    main_portrait = rgb_img.convert("RGBA")
    main_portrait.putalpha(final_a)
    
    # GHOST SYNCHRONIZATION
    ghost_w, ghost_h = config["ghost_frame"]["width"], config["ghost_frame"]["height"]
    ghost_raw = main_portrait.resize((ghost_w, ghost_h), Image.LANCZOS)
    r_g, g_g, b_g, a_g = ghost_raw.split()
    gray_g = Image.merge('RGB', (r_g, g_g, b_g)).convert('L').convert('RGB')
    a_g = a_g.point(lambda p: int(p * 0.25))
    ghost_portrait = gray_g.convert("RGBA")
    ghost_portrait.putalpha(a_g)
    
    # COMPOSITE
    card = template_img.copy()
    
    # Main portrait
    card.alpha_composite(main_portrait, (config["main_frame"]["x"], config["main_frame"]["y"]))
    
    # Pic2 bg & Ghost
    if pic2_bg:
        card.alpha_composite(pic2_bg, (965, 1008))
    card.alpha_composite(ghost_portrait, (config["ghost_frame"]["x"], config["ghost_frame"]["y"]))
    
    # Hologram
    if holo_img:
        card.alpha_composite(holo_img, (876, 1319))
        
    # ==========================================
    # STAGE B (FINAL BOOST & CLAHE & EDGE SEPARATION)
    # ==========================================
    # 1. Create a full-card mask of the face
    card_mask = Image.new('L', card.size, 0)
    card_mask.paste(final_a, (config["main_frame"]["x"], config["main_frame"]["y"]))
    
    card_rgb = card.convert("RGB")
    card_adj = card_rgb.copy()
    
    # 2. Apply remaining 50% adjustments
    brightness_B = 1 + (brightness - 1) * 0.5
    contrast_B = 1 + (contrast - 1) * 0.5
    saturation_B = 1 + (saturation - 1) * 0.5
    
    card_adj = ImageEnhance.Brightness(card_adj).enhance(brightness_B)
    card_adj = ImageEnhance.Contrast(card_adj).enhance(contrast_B)
    card_adj = ImageEnhance.Color(card_adj).enhance(saturation_B)
    
    card_adj_arr = np.array(card_adj)
    
    # 3. LOCAL CONTRAST BOOST (CLAHE) - Face only
    # Find bounding box to avoid applying CLAHE to background edges unnecessarily
    x, y, w, h = cv2.boundingRect(np.array(card_mask))
    if w > 0 and h > 0:
        face_roi = card_adj_arr[y:y+h, x:x+w]
        lab = cv2.cvtColor(face_roi, cv2.COLOR_RGB2LAB)
        l, a_chan, b_chan = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a_chan, b_chan))
        face_roi_clahe = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        card_adj_arr[y:y+h, x:x+w] = face_roi_clahe
        
    # 4. BOOST EDGE SEPARATION
    mask_arr = np.array(card_mask)
    edge_mask = cv2.dilate(mask_arr, np.ones((21,21), np.uint8), iterations=1) - cv2.erode(mask_arr, np.ones((21,21), np.uint8), iterations=1)
    edge_float = edge_mask.astype(np.float32) / 255.0
    
    float_adj = card_adj_arr.astype(np.float32)
    boosted_edge = (float_adj - 128.0) * 1.3 + 128.0
    boosted_edge = np.clip(boosted_edge, 0, 255)
    
    card_adj_arr = card_adj_arr * (1 - edge_float[:, :, None]) + boosted_edge * edge_float[:, :, None]
    card_adj_arr = card_adj_arr.astype(np.uint8)
    
    # 5. COMPOSITE BACK
    card_adj_final = Image.fromarray(card_adj_arr).convert("RGBA")
    card = Image.composite(card_adj_final, card, card_mask)

    # Text Rendering
    if text_data and fonts and not is_preview:
        draw = ImageDraw.Draw(card)
        text_color = (0, 0, 0)
        draw.text((509, 908), str(text_data.get('id_num', '')), font=fonts['id'], fill=text_color)
        draw.text((1377, 1063), str(text_data.get('last_name', '')), font=fonts['name'], fill=text_color)
        draw.text((1380, 1218), str(text_data.get('first_name', '')), font=fonts['name'], fill=text_color)
        draw.text((1374, 1438), str(text_data.get('middle_name', '')), font=fonts['name'], fill=text_color)
        draw.text((1377, 1589), str(text_data.get('dob', '')), font=fonts['dob'], fill=text_color)
        
        address_color = (0, 0, 0, 100) 
        draw.text((518, 1736), str(text_data.get('address', '')), font=fonts['reg'], fill=address_color)
        
    return card
