"""Script tạm để phân tích file PSD và lấy thông tin layer, font, tọa độ"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from psd_tools import PSDImage

psd = PSDImage.open('Philippines identity card (2).psd')
print(f"=== Canvas size: {psd.width} x {psd.height} ===\n")

def inspect_layer(layer, depth=0):
    prefix = "  " * depth
    try:
        name = layer.name
    except:
        name = "(unknown)"
    
    print(f"{prefix}Layer: '{name}' | Kind: {layer.kind} | Visible: {layer.visible}")
    print(f"{prefix}  Pos: L={layer.left}, T={layer.top}, R={layer.right}, B={layer.bottom} | Size: {layer.width}x{layer.height}")
    
    if layer.kind == 'type':
        try:
            text = layer.text
            print(f"{prefix}  TEXT: '{text}'")
        except Exception as e:
            print(f"{prefix}  Text error: {e}")
        try:
            td = layer.engine_dict
            if td:
                resource = td.get('ResourceDict', {})
                font_set = resource.get('FontSet', [])
                for i, font in enumerate(font_set):
                    fname = font.get('Name', 'Unknown')
                    print(f"{prefix}  FONT[{i}]: {fname}")
        except Exception as e:
            print(f"{prefix}  Font error: {e}")
    
    if layer.is_group():
        for child in layer:
            try:
                inspect_layer(child, depth + 1)
            except Exception as e:
                print(f"{prefix}  Error in child: {e}")

for layer in psd:
    try:
        inspect_layer(layer)
    except Exception as e:
        print(f"Error: {e}")
