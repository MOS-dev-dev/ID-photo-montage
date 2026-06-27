from PIL import Image, ImageDraw

def draw_boxes():
    img = Image.open('Philippines.png').convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # 1. Box for main face (What we think it is)
    
    # Yellow box: Better guess for main photo
    x1, y1 = 440, 960
    w1, h1 = 510, 680
    draw.rectangle([x1, y1, x1+w1, y1+h1], outline="yellow", width=5)
    
    # Ghost face current setting
    gx1, gy1 = 1004, 1096
    gw1, gh1 = 228, 269
    draw.rectangle([gx1, gy1, gx1+gw1, gy1+gh1], outline="green", width=5)
        
    img.save('box_test_2.png')
    print("Saved box_test_2.png")

if __name__ == "__main__":
    draw_boxes()
