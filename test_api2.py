import requests
import json
import time

url = "http://localhost:8000"

def test_api():
    files = {'file': ('test.jpg', open('pinterest_face.jpg', 'rb'), 'image/jpeg')}
    print("Uploading...")
    res = requests.post(f"{url}/api/upload", files=files)
    print("Upload res:", res.status_code, res.text)
    if res.status_code != 200: return
    
    img_id = res.json()["id"]
    df = res.json()["detected_face"]
    
    # We want to scale the face to fit the 490x650 canvas.
    scale = min(490 / df["width"], 650 / df["height"])
    # Center the face
    x = (490 - df["width"] * scale) / 2
    y = (650 - df["height"] * scale) / 2
    
    frame = {
        "x": x, "y": y, "scale": scale, "rotation": 0,
        "width": df["width"], "height": df["height"],
        "canvas_width": 490, "canvas_height": 650
    }
    
    print("Frame:", frame)
    
    # Normal
    data_normal = {
        "id": img_id,
        "frame_json": json.dumps(frame),
        "image_adjust": json.dumps({"brightness": 1.0, "contrast": 1.0, "saturation": 1.0})
    }
    print("Generating normal...")
    res1 = requests.post(f"{url}/api/generate", data=data_normal)
    print(res1.status_code, res1.text)
    
    time.sleep(1)
    
    # Extreme
    data_extreme = {
        "id": img_id,
        "frame_json": json.dumps(frame),
        "image_adjust": json.dumps({"brightness": 2.0, "contrast": 2.0, "saturation": 2.0})
    }
    print("Generating extreme...")
    res2 = requests.post(f"{url}/api/generate", data=data_extreme)
    print(res2.status_code, res2.text)

if __name__ == "__main__":
    test_api()
