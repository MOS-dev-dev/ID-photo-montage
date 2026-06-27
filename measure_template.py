"""Do toa do chinh xac tren phoi the xuat tu Photoshop (3000x4000)"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image

img = Image.open('blank_template.png').convert('RGBA')
px = img.load()
w, h = img.size
print(f"Template size: {w}x{h}")

# Tim bien card (chuyen tu nen go sang card)
# Scan theo Y o giua anh (x=1500)
print("\n=== Tim CARD TOP (scan doc x=1500) ===")
for y in range(400, 600):
    r, g, b, a = px[1500, y]
    if a > 200 and r > 180 and g > 180 and b > 160:
        # Ktra dong truoc co phai nen go khong (mau nau)
        r2, g2, b2, a2 = px[1500, y-1]
        if r2 < 180 or (r2 > 100 and g2 < 100):
            print(f"  Card top at y={y}: RGBA({r},{g},{b},{a})")
            break

# Tim card bottom
print("\n=== Tim CARD BOTTOM (scan doc x=1500) ===")
for y in range(2200, 1800, -1):
    r, g, b, a = px[1500, y]
    if a > 200 and r > 180 and g > 180 and b > 160:
        r2, g2, b2, a2 = px[1500, y+1]
        if a2 < 100 or (r2 > 100 and r2 < 170 and g2 < 100):
            print(f"  Card bottom at y={y}: RGBA({r},{g},{b},{a})")
            break

# Tim card left
print("\n=== Tim CARD LEFT (scan ngang y=1200) ===")
for x in range(200, 500):
    r, g, b, a = px[x, 1200]
    if a > 200 and r > 180 and g > 180 and b > 160:
        r2, g2, b2, a2 = px[x-1, 1200]
        if a2 < 100 or r2 < 150:
            print(f"  Card left at x={x}: RGBA({r},{g},{b},{a})")
            break

# Tim card right
print("\n=== Tim CARD RIGHT (scan ngang y=1200) ===")
for x in range(2800, 2400, -1):
    r, g, b, a = px[x, 1200]
    if a > 200 and r > 180 and g > 180 and b > 160:
        r2, g2, b2, a2 = px[x+1, 1200]
        if a2 < 100 or r2 < 150:
            print(f"  Card right at x={x}: RGBA({r},{g},{b},{a})")
            break

# Xac dinh vi tri cac label text tren card
# Scan tim text toi mau (RGB < 100) trong vung ben phai card
print("\n=== Tim vi tri LABELS (text toi mau, x > 1200) ===")
dark_rows = {}
for y in range(500, 2000):
    count = 0
    for x in range(1200, 2600, 2):
        r, g, b, a = px[x, y]
        if a > 200 and r < 80 and g < 80 and b < 80:
            count += 1
    if count > 10:
        dark_rows[y] = count

# Nhom cac dong lien tiep
if dark_rows:
    sorted_ys = sorted(dark_rows.keys())
    groups = []
    cur = [sorted_ys[0]]
    for i in range(1, len(sorted_ys)):
        if sorted_ys[i] - sorted_ys[i-1] <= 5:
            cur.append(sorted_ys[i])
        else:
            if len(cur) >= 3:
                groups.append(cur)
            cur = [sorted_ys[i]]
    if len(cur) >= 3:
        groups.append(cur)
    
    for i, g in enumerate(groups):
        print(f"  Label group {i}: y={min(g)}-{max(g)} (height={max(g)-min(g)})")

# Tim vung anh the (vung co hologram/watermark o ben trai)
print("\n=== Tim vi tri ANH THE (scan vung trai, x=300-900) ===")
# Tim bien tren cua vung anh (chuyen tu header sang vung anh)
for y in range(800, 1300):
    has_border = False
    for x in range(400, 500):
        r, g, b, a = px[x, y]
        # Tim duong vien anh the (thuong la mau sang hon hoac toi hon)
        r2, g2, b2, a2 = px[x, y-1]
        diff = abs(r-r2) + abs(g-g2) + abs(b-b2)
        if diff > 50:
            has_border = True
            break
    if has_border:
        print(f"  Possible photo border at y={y}")
        if y > 900:  # Chi lay cai dau tien sau y=900
            break

# In mau sac tai cac vi tri PSD da biet
print("\n=== Mau sac tai vi tri PSD ===")
psd_points = {
    'ID': (509, 908),
    'LastName': (1377, 1063),
    'FirstName': (1380, 1218),
    'MiddleName': (1374, 1438),
    'DOB': (1377, 1589),
    'Address': (518, 1736),
    'Photo_TL': (472, 1183),
    'Photo_BR': (904, 1693),
}
for name, (x, y) in psd_points.items():
    if 0 <= x < w and 0 <= y < h:
        print(f"  {name} ({x},{y}): RGBA{px[x,y]}")
