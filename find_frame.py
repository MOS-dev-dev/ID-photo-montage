"""Tim vi tri khung anh tren phoi the"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open('blank_template.png')
px = img.load()
w, h = img.size

# Scan horizontal edges on left side (x=10 to x=280)
print("=== HORIZONTAL EDGES (tim bien tren/duoi cua khung anh) ===")
for y in range(130, 500):
    # Tinh su khac biet giua dong y va dong y-1
    diff = 0
    for x in range(10, 280):
        r1, g1, b1 = px[x, y][:3]
        r2, g2, b2 = px[x, y-1][:3]
        diff += abs(r1-r2) + abs(g1-g2) + abs(b1-b2)
    if diff > 3000:
        print(f"  y={y}: diff={diff}")

# Scan vertical edges (tim bien trai/phai cua khung anh)
print("\n=== VERTICAL EDGES (tim bien trai/phai cua khung anh) ===")
for x in range(10, 310):
    diff = 0
    for y in range(150, 460):
        r1, g1, b1 = px[x, y][:3]
        r2, g2, b2 = px[x-1, y][:3]
        diff += abs(r1-r2) + abs(g1-g2) + abs(b1-b2)
    if diff > 3000:
        print(f"  x={x}: diff={diff}")

# Cung xem mau tai cac diem can khung anh theo PSD
print("\n=== Mau tai vi tri PSD (40,259) ===")
for dy in range(-30, 31, 10):
    for dx in range(-20, 21, 10):
        x, y = 40+dx, 259+dy
        if 0 <= x < w and 0 <= y < h:
            print(f"  ({x},{y}): RGB{px[x,y][:3]}")
