"""Script do toa do chinh xac tren anh mau (917x544)"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image
import json

# Mo anh mau
img = Image.open('1/DELA CRUZ.LEAH.SANTOS.png')
w, h = img.size
print(f"Image size: {w}x{h}")

# Scan anh de tim vi tri text (tim cac vung toi mau)
# Ta se xuat pixel data de phan tich thu cong
# Tim vung chua ID number (mau do)
pixels = img.load()

# Scan tim diem mau do (R > 150, G < 100, B < 100)
red_points = []
for y in range(h):
    for x in range(w):
        r, g, b = pixels[x, y][:3]
        if r > 150 and g < 80 and b < 80:
            red_points.append((x, y))

if red_points:
    min_x = min(p[0] for p in red_points)
    max_x = max(p[0] for p in red_points)
    min_y = min(p[1] for p in red_points)
    max_y = max(p[1] for p in red_points)
    print(f"RED text (ID number) area: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"  Top-left: ({min_x}, {min_y})")
    print(f"  Size: {max_x-min_x}x{max_y-min_y}")
    
    # Sample red color
    mid_x = (min_x + max_x) // 2
    mid_y = (min_y + max_y) // 2
    print(f"  Sample red color at ({mid_x},{mid_y}): {pixels[mid_x, mid_y]}")
else:
    print("No red text found!")

# Scan tim vung text den dam (R < 60, G < 60, B < 60) - chi vung ben phai (x > 400)
black_rows = {}
for y in range(h):
    for x in range(350, w):
        r, g, b = pixels[x, y][:3]
        if r < 50 and g < 50 and b < 50:
            if y not in black_rows:
                black_rows[y] = []
            black_rows[y].append(x)

# Tim cac hang text (nhom cac y lien tiep)
if black_rows:
    sorted_ys = sorted(black_rows.keys())
    groups = []
    current_group = [sorted_ys[0]]
    for i in range(1, len(sorted_ys)):
        if sorted_ys[i] - sorted_ys[i-1] <= 3:
            current_group.append(sorted_ys[i])
        else:
            if len(current_group) >= 5:  # Chi lay nhung nhom co it nhat 5 dong pixel
                groups.append(current_group)
            current_group = [sorted_ys[i]]
    if len(current_group) >= 5:
        groups.append(current_group)
    
    print(f"\nBlack text groups (right side, x>350):")
    for i, group in enumerate(groups):
        min_y = min(group)
        max_y = max(group)
        all_xs = []
        for y in group:
            all_xs.extend(black_rows[y])
        min_x = min(all_xs)
        max_x = max(all_xs)
        print(f"  Group {i}: y={min_y}-{max_y} (height={max_y-min_y}), x={min_x}-{max_x}")
