from PIL import Image

def extend_background(img, target_w, target_h):
    w, h = img.size
    new_img = Image.new('RGB', (target_w, target_h))
    
    # Calculate paste position (center)
    paste_x = (target_w - w) // 2
    paste_y = (target_h - h) // 2
    
    # Paste the original image
    new_img.paste(img, (paste_x, paste_y))
    
    # Extend top
    if paste_y > 0:
        top_edge = img.crop((0, 0, w, 1))
        top_extended = top_edge.resize((w, paste_y))
        new_img.paste(top_extended, (paste_x, 0))
    
    # Extend bottom
    if paste_y + h < target_h:
        bottom_h = target_h - (paste_y + h)
        bottom_edge = img.crop((0, h-1, w, h))
        bottom_extended = bottom_edge.resize((w, bottom_h))
        new_img.paste(bottom_extended, (paste_x, paste_y + h))
        
    # Extend left
    if paste_x > 0:
        left_edge = new_img.crop((paste_x, 0, paste_x+1, target_h))
        left_extended = left_edge.resize((paste_x, target_h))
        new_img.paste(left_extended, (0, 0))
        
    # Extend right
    if paste_x + w < target_w:
        right_w = target_w - (paste_x + w)
        right_edge = new_img.crop((paste_x+w-1, 0, paste_x+w, target_h))
        right_extended = right_edge.resize((right_w, target_h))
        new_img.paste(right_extended, (paste_x+w, 0))
        
    return new_img

img = Image.open('anh_nam/1024287508988362005.jpg')
# Resize it small to simulate small face
img.thumbnail((300, 400))
out = extend_background(img, 490, 680)
out.save('_debug_extend.png')
