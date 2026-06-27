"""Extract font NAME from PSD"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from psd_tools import PSDImage

psd = PSDImage.open('Philippines identity card (2).psd')

def get_font_name(layer, depth=0):
    if layer.kind == 'type':
        try:
            td = layer.engine_dict
            if td:
                resource = td.get('ResourceDict', {})
                font_set = resource.get('FontSet', [])
                print(f"Layer: '{layer.name}'")
                print(f"  FontSet length: {len(font_set)}")
                for i, font in enumerate(font_set):
                    # Try different ways to get font name
                    print(f"  FontSet[{i}] keys: {list(font.keys()) if hasattr(font, 'keys') else 'not a dict'}")
                    print(f"  FontSet[{i}] type: {type(font)}")
                    print(f"  FontSet[{i}] value: {font}")
                    if hasattr(font, 'Name'):
                        print(f"  FontSet[{i}] Name attr: {font.Name}")
                    for key in dir(font):
                        if not key.startswith('_'):
                            try:
                                val = getattr(font, key)
                                if not callable(val):
                                    print(f"  FontSet[{i}].{key} = {val}")
                            except:
                                pass
                print()
                return  # Only need first text layer
        except Exception as e:
            print(f"Error: {e}")
    if layer.is_group():
        for child in layer:
            get_font_name(child, depth+1)

for layer in psd:
    get_font_name(layer)
