import requests
import re
import sys
url = 'https://www.pinterest.com/pin/930697079316010510/'
r = requests.get(url)
# Pinterest uses 736x or originals. Let's find any 736x jpg
matches = re.findall(r'(https://i\.pinimg\.com/736x/[^"]+\.jpg)', r.text)
if not matches:
    matches = re.findall(r'(https://i\.pinimg\.com/originals/[^"]+\.jpg)', r.text)
if matches:
    img_url = matches[0]
    print(f"Downloading {img_url}")
    with open('pinterest_face.jpg', 'wb') as f:
        f.write(requests.get(img_url).content)
    print("Success")
else:
    print("No images found")
