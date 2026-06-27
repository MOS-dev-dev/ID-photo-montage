import re
html = open('alt_tpdne.html', 'r', encoding='utf-8').read()
m = re.search(r'id="avatar"\s+src="([^"]+)"', html)
if m:
    print(m.group(1))
else:
    print("Not found")
