import math
from PIL import Image

def apply_frame(face_nobg, target_w, target_h, frame_config):
    """
    Applies user-defined framing (scale, rotation, translation) to the foreground image
    and returns an RGBA canvas of size (target_w, target_h).
    """
    x = frame_config.get("x", 0)
    y = frame_config.get("y", 0)
    scale = frame_config.get("scale", 1.0)
    rotation = frame_config.get("rotation", 0)
    
    # 1. Resize based on scale
    orig_w, orig_h = face_nobg.size
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    
    # Use LANCZOS for high quality downsampling or upsampling
    resized_img = face_nobg.resize((new_w, new_h), Image.LANCZOS)
    
    # 2. Rotate if necessary
    if rotation != 0:
        # expand=True ensures the image bounds are expanded to fit the rotated corners
        resized_img = resized_img.rotate(-rotation, resample=Image.BICUBIC, expand=True)
        # after rotation, we need to adjust x,y so the center remains the same if fabric.js uses originX/Y = center
        # but typically fabric.js left/top refers to bounding box top left unless specified. 
        # We will assume x, y is the top-left of the bounding box.
        
    # 3. Create canvas and paste
    crop_canvas = Image.new('RGBA', (target_w, target_h), (255, 255, 255, 0))
    crop_canvas.paste(resized_img, (int(x), int(y)), resized_img)
    
    return crop_canvas
