from PIL import Image

img = Image.open('Philippines.png').convert('RGB')
px = img.load()

# Tim ID (black, left of center)
id_pos = None
for y in range(400, 2000):
    count = 0
    for x in range(350, 1000):
        r,g,b = px[x,y]
        if r<50 and g<50 and b<50:
            count += 1
            if count > 50:
                id_pos = (x, y)
                break
    if id_pos: break

# Tim label CASTRO (black, right side)
last_pos = None
for y in range(800, 1500):
    count = 0
    for x in range(1300, 2000):
        r,g,b = px[x,y]
        if r<50 and g<50 and b<50:
            count += 1
            if count > 50:
                last_pos = (x, y)
                break
    if last_pos: break

print(f"ID pos approx: {id_pos}")
print(f"LAST pos approx: {last_pos}")
