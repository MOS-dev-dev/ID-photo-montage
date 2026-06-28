import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. MediaPipe Face Landmarker
try:
    base_options = python.BaseOptions(model_asset_path='face_landmarker.task')
    options = vision.FaceLandmarkerOptions(base_options=base_options,
                                           output_face_blendshapes=False,
                                           output_facial_transformation_matrixes=False,
                                           num_faces=1)
    face_landmarker = vision.FaceLandmarker.create_from_options(options)
except Exception as e:
    print(f"Warning: Could not load face_landmarker.task: {e}")
    face_landmarker = None

# 2. MediaPipe Face Detector
try:
    fd_base_options = python.BaseOptions(model_asset_path='blaze_face_short_range.tflite')
    fd_options = vision.FaceDetectorOptions(base_options=fd_base_options, min_detection_confidence=0.5)
    face_detector = vision.FaceDetector.create_from_options(fd_options)
except Exception as e:
    print(f"Warning: Could not load blaze_face_short_range.tflite: {e}")
    face_detector = None

# 3. OpenCV DNN Face Detector
try:
    cv_net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'res10_300x300_ssd_iter_140000.caffemodel')
except Exception as e:
    print(f"Warning: Could not load OpenCV DNN models: {e}")
    cv_net = None

def get_image_versions(img_bgr):
    versions = []
    versions.append(img_bgr) # A. Original
    
    # B. CLAHE
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(l)
    versions.append(cv2.cvtColor(cv2.merge((cl,a,b)), cv2.COLOR_LAB2BGR))
    
    # C. Brightness
    versions.append(cv2.convertScaleAbs(img_bgr, alpha=1.0, beta=30))
    
    # D. Contrast
    versions.append(cv2.convertScaleAbs(img_bgr, alpha=1.3, beta=0))
    
    # E. Sharpened
    kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
    versions.append(cv2.filter2D(img_bgr, -1, kernel))
    
    return versions

def detect_face_multi_stage(original_bgr):
    versions = get_image_versions(original_bgr)
    
    for v_idx, img_bgr in enumerate(versions):
        h, w, _ = img_bgr.shape
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        
        # STAGE 1: Landmarker
        if face_landmarker:
            try:
                res_lm = face_landmarker.detect(mp_image)
                if res_lm and res_lm.face_landmarks:
                    x_min, y_min = w, h
                    x_max, y_max = 0, 0
                    for lm in res_lm.face_landmarks[0]:
                        x, y = int(lm.x * w), int(lm.y * h)
                        x_min, y_min = min(x_min, x), min(y_min, y)
                        x_max, y_max = max(x_max, x), max(y_max, y)
                    return {'x': x_min, 'y': y_min, 'w': x_max - x_min, 'h': y_max - y_min, 'detector': 'mediapipe_landmarker', 'version': v_idx}
            except: pass
            
        # STAGE 2: MP Detection
        if face_detector:
            try:
                res_fd = face_detector.detect(mp_image)
                if res_fd and res_fd.detections:
                    bbox = res_fd.detections[0].bounding_box
                    return {'x': int(bbox.origin_x), 'y': int(bbox.origin_y), 'w': int(bbox.width), 'h': int(bbox.height), 'detector': 'mediapipe_detection', 'version': v_idx}
            except: pass
            
        # STAGE 3: OpenCV DNN
        if cv_net:
            try:
                blob = cv2.dnn.blobFromImage(cv2.resize(img_bgr, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
                cv_net.setInput(blob)
                detections = cv_net.forward()
                best_conf = 0
                best_box = None
                for i in range(detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    if confidence > 0.5 and confidence > best_conf:
                        best_conf = confidence
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype("int")
                        best_box = {'x': startX, 'y': startY, 'w': endX - startX, 'h': endY - startY, 'detector': 'opencv_dnn', 'version': v_idx}
                if best_box:
                    return best_box
            except: pass
            
    return None
