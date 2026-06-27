import requests
import json
import os

os.makedirs("tmp", exist_ok=True)
# copy a test image to tmp
# wait, I don't have a specific test image, let me just check the backend folder, or just use the whole process:
# upload -> generate
import time

url = "http://localhost:8000"

def test_api():
    # first upload an image
    files = {'file': ('test.jpg', open('pinterest_face.jpg', 'rb'), 'image/jpeg')}
    print("Uploading...")
    res = requests.post(f"{url}/api/upload", files=files)
    print("Upload res:", res.status_code, res.text)
    if res.status_code != 200:
        return
    
    img_id = res.json()["id"]
    # generate normally. We need a frame that maps to (0,0) in main_frame.
    # main_frame config is {"width": 490, "height": 650, "x": 485, "y": 960}
    # template size is 3000x4000.
    # mapped_frame = map_frame(frame)
    # mapped_frame["x"] = frame.x * (3000/490) - 485
    # We want mapped_frame["x"] = 0 -> frame.x = 485 * (490/3000) = 79.21
    # We want mapped_frame["y"] = 0 -> frame.y = 960 * (650/4000) = 156.0
    frame = {"x": 79.21, "y": 156.0, "scale": 0.5, "rotation": 0, "width": 490, "height": 650, "canvas_width": 490, "canvas_height": 650}
    
    # generate normally
    data_normal = {
        "id": img_id,
        "frame_json": json.dumps(frame),
        "image_adjust": json.dumps({"brightness": 1.0, "contrast": 1.0, "saturation": 1.0}),
        "text_data": "{}"
    }
    print("Generating normal...")
    res1 = requests.post(f"{url}/api/generate", data=data_normal)
    print(res1.status_code, res1.text)
    
    # generate extreme
    data_extreme = {
        "id": img_id,
        "frame_json": json.dumps(frame),
        "image_adjust": json.dumps({"brightness": 2.0, "contrast": 2.0, "saturation": 2.0}),
        "text_data": "{}"
    }
    print("Generating extreme...")
    res2 = requests.post(f"{url}/api/generate", data=data_extreme)
    print(res2.status_code, res2.text)

if __name__ == "__main__":
    test_api()
