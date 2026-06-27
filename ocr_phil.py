import pytesseract
from PIL import Image

img = Image.open('Philippines.png')
data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

for i in range(len(data['text'])):
    text = data['text'][i].strip()
    if len(text) > 2:
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        print(f"'{text}': x={x}, y={y}, w={w}, h={h}")
