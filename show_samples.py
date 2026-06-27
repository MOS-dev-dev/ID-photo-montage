import os
import glob
from PIL import Image, ImageDraw, ImageFilter
from tool_tao_the import process_portrait, TEMPLATE_PATH, CFG_MAIN, CFG_GHOST, GHOST_BG_LEFT, GHOST_BG_TOP, HOLO_LEFT, HOLO_TOP

def make_sample():
    os.makedirs('sample_outputs', exist_ok=True)
    
    # Pick a few sample images
    src_files = []
    for d in ['anh_nam_tre', 'anh_nu_tre']:
        if os.path.exists(d):
            src_files.extend(glob.glob(os.path.join(d, '*.*')))
            
    src_files = [f for f in src_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not src_files:
        print("No source files found!")
        return

    # Just take 15 images for demonstration
    samples = src_files[:15]
    
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
    
    for idx, f in enumerate(samples):
        base = os.path.basename(f)
        print(f"Processing {base}...")
        debug_id = f"test_{idx}"
        result = process_portrait(f, template_img=template_img, debug_id=debug_id)
        if result is None or len(result) < 4 or result[0] is None:
            print("Failed.")
            continue
            
        main_p, ghost_p, reframes, detector = result
        
        card = template_img.copy()
        card.alpha_composite(main_p, (CFG_MAIN["x"], CFG_MAIN["y"]))
        card.alpha_composite(pic2_bg, (GHOST_BG_LEFT, GHOST_BG_TOP))
        card.alpha_composite(ghost_p, (CFG_GHOST["x"], CFG_GHOST["y"]))
        card.alpha_composite(holo_img, (HOLO_LEFT, HOLO_TOP))
        
        # Save to debug folder
        os.makedirs('debug', exist_ok=True)
        debug_card_path = os.path.join('debug', f"{debug_id}_08_final_card.png")
        card.convert("RGB").save(debug_card_path, "PNG")
        
        out_path = os.path.join('sample_outputs', f"sample_{idx}.png")
        card.convert("RGB").save(out_path, "PNG")
        print(f"Saved {out_path} and debug outputs")

if __name__ == "__main__":
    make_sample()
