import urllib.request
import os

MODELS = {
    "deploy.prototxt": "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt",
    "res10_300x300_ssd_iter_140000.caffemodel": "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
}

def download_models():
    for filename, url in MODELS.items():
        if not os.path.exists(filename):
            print(f"Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filename)
                print(f" -> Success!")
            except Exception as e:
                print(f" -> Error downloading {filename}: {e}")
        else:
            print(f"{filename} already exists. Skipping.")

if __name__ == "__main__":
    download_models()
