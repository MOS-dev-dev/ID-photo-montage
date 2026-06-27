"""Do toa do tren file Philippines.png"""
from PIL import Image

img = Image.open('Philippines.png').convert('RGB')
px = img.load()

# Tim bien card (quet doc x=1500)
for y in range(0, 1000):
    r,g,b = px[1500,y]
    if r>180 and g>180 and b>160: # mau the
        r2,g2,b2 = px[1500, y-1]
        if r2<150: # mau go
            print(f"Card Top: {y}")
            break

for y in range(2500, 1000, -1):
    r,g,b = px[1500,y]
    if r>180 and g>180 and b>160:
        r2,g2,b2 = px[1500, y+1]
        if r2<150:
            print(f"Card Bottom: {y}")
            break

for x in range(0, 1000):
    r,g,b = px[x, 500]
    if r>180 and g>180 and b>160:
        r2,g2,b2 = px[x-1, 500]
        if r2<150:
            print(f"Card Left: {x}")
            break

# Tim chu CASTRO (quet tu trai sang phai tren dong y=530)
for x in range(1300, 1500):
    r,g,b = px[x, 530]
    if r<100 and g<100 and b<100:
        print(f"CASTRO left: {x}")
        break

# Tim chu 4950- (quet tu trai sang phai tren dong y=470)
for x in range(350, 500):
    r,g,b = px[x, 470]
    if r<100 and g<100 and b<100:
        print(f"ID left: {x}")
        break
