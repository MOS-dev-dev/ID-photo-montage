import os
import cv2
import numpy as np
from PIL import Image
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

def normalize_portrait(img_bgr):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl,a,b))
    final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return final

def remove_background(img_bgr):
    """
    Takes a BGR image, normalizes it, and removes the background using rembg or mediapipe fallback.
    Returns a PIL RGBA Image.
    """
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
            
    return face_nobg
