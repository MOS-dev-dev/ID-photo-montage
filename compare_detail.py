"""So sanh chi tiet Philippines.png vs output"""
from PIL import Image

ref = Image.open('Philippines.png')
out = Image.open('output_cards/RAMOS.ISABEL MARIE.AGUILAR.png')

print(f"Philippines.png: {ref.size}")   # 3000x4000
print(f"Output:          {out.size}")   # 917x544

# Kiem tra: Philippines.png co phai output cuoi cung khong?
# Hay ban xuat nguyen canvas 3000x4000 bao gom ca nen go?
# -> Co! Philippines.png la 3000x4000, tuc ban KHONG crop, xuat nguyen canvas

# Kiem tra vung anh the chinh xac
px = ref.load()

# Tim vien anh the (vien vang/nau dam quanh anh)
# Scan doc x=472 (photo left) tu tren xuong
print("\n=== Vien anh the ===")
for y in range(1100, 1200):
    r,g,b,a = px[500, y]
    print(f"  x=500, y={y}: RGB({r},{g},{b})")

# Tim photo frame top (vien vang)
print("\n=== Photo frame scan x=600, doc ===")
for y in range(1150, 1200):
    r,g,b,a = px[600, y]
    print(f"  y={y}: RGB({r},{g},{b})")

# Tim vien anh trai
print("\n=== Photo frame scan y=1300, ngang ===")
for x in range(440, 480):
    r,g,b,a = px[x, 1300]
    print(f"  x={x}: RGB({r},{g},{b})")
