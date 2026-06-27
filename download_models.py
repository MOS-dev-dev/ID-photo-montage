import urllib.request
import os

MODELS = {
    "blaze_face_short_range.tflite": "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
    "opencv_face_detector_uint8.pb": "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20180205_fp16/opencv_face_detector_uint8.pb",
    "opencv_face_detector.pbtxt": "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/opencv_face_detector.pbtxt"
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
