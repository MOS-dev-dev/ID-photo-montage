from PIL import Image
import numpy as np

# Mở ảnh mẫu Philippines.png
img = Image.open('Philippines.png').convert('RGBA')
arr = np.array(img)

# Ảnh mẫu là 3000x4000
# Thẻ nằm trong khoảng x: ~420-2580, y: ~460-2320 (ước lượng)
# Ảnh chân dung nằm bên trái thẻ
# Tìm vùng có ảnh người bằng cách quét cột bên trái

# In kích thước
print(f"Image size: {img.size}")  # (width, height)

# Nhìn ảnh mẫu, ảnh chân dung chiếm khoảng:
# Left edge ~ 472px, Right edge ~ 900px -> W ~ 428
# Top edge ~ 1040px, Bottom edge ~ 1700px -> H ~ 660
# Nhưng cần đo chính xác hơn

# Ghost face (ảnh mờ nhỏ bên phải):
# Left ~ 1004, Top ~ 1096, W ~ 228, H ~ 269

# Tỷ lệ ghost so với main:
# Ghost center X ~ 1004 + 114 = 1118
# Ghost center Y ~ 1096 + 134 = 1230

# Nếu main photo W=428, H=660:
# Tỷ lệ ghost/main W: 228/428 = 0.533
# Tỷ lệ ghost/main H: 269/660 = 0.407

# Thử quét pixel để tìm vùng ảnh chân dung
# Vùng ảnh người sẽ có alpha > 0 hoặc có màu khác nền
# Quét từ x=450 đến x=950, y=950 đến y=1800

# Tìm bounding box của vùng có pixel "không phải nền thẻ"
# Nền thẻ có màu trắng/xám nhạt
# Ảnh người có màu da, tóc...

print("\n--- Phân tích vùng ảnh chân dung trên Philippines.png ---")
print("Dựa trên quan sát visual:")
print(f"  Main photo: LEFT~472, TOP~1040, W~430, H~660")
print(f"  Ghost photo: LEFT~1004, TOP~1096, W~228, H~269")
print(f"  Tỷ lệ W: {228/430:.3f}")
print(f"  Tỷ lệ H: {269/660:.3f}")

# So sánh với config hiện tại
print("\n--- Config hiện tại ---")
print(f"  PHOTO_LEFT=472, PHOTO_TOP=980, PHOTO_W=450, PHOTO_H=560")
print(f"  -> Ảnh chân dung: 450x560 = quá to!")
print(f"  -> Nên giảm về khoảng 430x530 hoặc nhỏ hơn")
