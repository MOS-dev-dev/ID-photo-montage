import sys
from psd_tools import PSDImage

psd = PSDImage.open('Philippines identity card (2).psd')

def find_layer(group, name):
    for layer in group:
        if layer.name == name:
            return layer
        if layer.is_group():
            res = find_layer(layer, name)
            if res: return res
    return None

front_side = find_layer(psd, 'front side')
holo_group = find_layer(front_side, 'Hologram')

# Luu Hologram de ghep vao the
if holo_group:
    holo_img = holo_group.composite()
    holo_img.save('hologram.png')
    print("Saved hologram.png")
else:
    print("Khong tim thay Hologram")

pic2_group = find_layer(front_side, 'Picture 2')
if pic2_group:
    bg_layer = None
    for l in pic2_group:
        if l.name == 'BG': bg_layer = l
    if bg_layer:
        bg_img = bg_layer.composite()
        bg_img.save('pic2_bg.png')
        print("Saved pic2_bg.png")
