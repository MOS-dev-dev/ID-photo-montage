import requests
import re

url = 'https://www.pinterest.com/pin/723672233855926315/'
r = requests.get(url)
matches = re.findall(r'(https://i\.pinimg\.com/736x/[^"]+\.jpg)', r.text)
if not matches:
    matches = re.findall(r'(https://i\.pinimg\.com/originals/[^"]+\.jpg)', r.text)
print("Matches:", matches)
