import os
import uuid
import json
import cv2
import numpy as np
from PIL import Image, ImageFont, ImageFilter
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import zipfile
import io
import asyncio
import threading
import gc
import shutil
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks

class BatchContext:
    def __init__(self, batch_id):
        self.batch_id = batch_id
        self.progress = {
            "current": 0,
            "total": 0,
            "percent": 0,
            "status": "pending"
        }
        self.lock = threading.Lock()
        self.output_dir = f"outputs/batch_{batch_id}"
        self.counter = 0

app = FastAPI()

batch_registry = {}

@app.on_event("startup")
async def startup_event():
    # Scan outputs/ to rebuild batch_registry only if needed for downloads/results
    if os.path.exists("outputs"):
        for folder in os.listdir("outputs"):
            if folder.startswith("batch_") and os.path.isdir(os.path.join("outputs", folder)):
                batch_id = folder.split("batch_")[-1]
                if batch_id and batch_id not in batch_registry:
                    bc = BatchContext(batch_id)
                    bc.progress["status"] = "completed"
                    bc.progress["percent"] = 100
                    batch_registry[batch_id] = bc

from pipeline.detector import detect_face_multi_stage
from pipeline.background import remove_background
from pipeline.crop import apply_frame
from pipeline.render import render_final_card, map_frame

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("tmp", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
app.mount("/tmp", StaticFiles(directory="tmp"), name="tmp")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Load configurations and templates
try:
    with open("../template_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    template_img = Image.open("../blank_template.png").convert("RGBA")
    pic2_bg = Image.open("../pic2_bg.png").convert("RGBA")
    holo_img = Image.open("../hologram.png").convert("RGBA")
    holo_img = holo_img.filter(ImageFilter.GaussianBlur(1))
    r, g, b, a = holo_img.split()
    a = a.point(lambda p: int(p * 0.25))
    holo_img.putalpha(a)
except Exception as e:
    print(f"Warning: Could not load assets from parent dir: {e}")
    config = {"main_frame": {"width": 490, "height": 650, "x": 485, "y": 960}, 
              "ghost_frame": {"width": 228, "height": 269, "x": 1004, "y": 1096}}
    template_img, pic2_bg, holo_img = None, None, None

fonts = {}
try:
    fonts['id'] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 70)
    fonts['name'] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 70)
    fonts['dob'] = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 74)
    fonts['reg'] = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 61)
except Exception as e:
    print(f"Warning: Could not load fonts: {e}")

class PreviewRequest(BaseModel):
    id: str
    frame: Dict[str, float]
    image_adjust: Dict[str, float]

class GenerateRequest(BaseModel):
    id: str
    frame: Dict[str, float]
    image_adjust: Dict[str, float]
    text_data: Dict[str, Any] = {}

class SaveFrameRequest(BaseModel):
    frame: Dict[str, float]

@app.get("/")
async def root():
    return {"status": "OK"}

@app.get("/api/frame")
async def get_frame():
    try:
        with open("outputs/frame.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "x": 0, "y": 0, "scale": 0.75, "rotation": 0,
            "width": 0, "height": 0, "canvas_width": 490, "canvas_height": 650
        }

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Invalid image")
        
    face_id = str(uuid.uuid4())
    
    # Run Face Detection on original image (normalized version in detector)
    region = detect_face_multi_stage(img_bgr)
    if not region:
        # Fallback if no face detected
        region = {'x': 0, 'y': 0, 'w': img_bgr.shape[1], 'h': img_bgr.shape[0]}
        
    # Remove background
    face_nobg = remove_background(img_bgr)
    
    fg_path = f"tmp/{face_id}_fg.png"
    face_nobg.save(fg_path)
    
    return {
        "id": face_id,
        "preview_url": f"http://localhost:8000/tmp/{face_id}_fg.png",
        "detected_face": {
            "x": region['x'],
            "y": region['y'],
            "width": region['w'],
            "height": region['h']
        }
    }

@app.post("/api/preview")
async def generate_preview(req: PreviewRequest):
    fg_path = f"tmp/{req.id}_fg.png"
    if not os.path.exists(fg_path):
        raise HTTPException(status_code=404, detail="Image not found")
        
    face_nobg = Image.open(fg_path).convert("RGBA")
    
    template_w, template_h = template_img.size if template_img else (3000, 4000)
    mapped_frame = map_frame(req.frame, template_w, template_h)
    mapped_frame["x"] -= config["main_frame"]["x"]
    mapped_frame["y"] -= config["main_frame"]["y"]
    
    # Apply Frame
    framed_canvas = apply_frame(face_nobg, config["main_frame"]["width"], config["main_frame"]["height"], mapped_frame)
    
    # Render Preview (no text)
    if template_img is None:
        return {"preview_url": ""} # Return empty if no template
        
    card = render_final_card(framed_canvas, template_img, config, req.image_adjust, 
                             pic2_bg, holo_img, is_preview=True)
                             
    out_path = f"tmp/{req.id}_preview.png"
    card.convert("RGB").save(out_path, "PNG")
    
    return {"preview_url": f"http://localhost:8000/tmp/{req.id}_preview.png"}

@app.post("/api/generate")
async def generate_card(
    id: str = Form(None),
    frame_json: str = Form(None),
    image_adjust: str = Form("{}"),
    text_data: str = Form("{}"),
    image: UploadFile = File(None)
):
    if frame_json is None:
        raise HTTPException(status_code=400, detail="Missing frame_json")
        
    print("FRAME RECEIVED")
    print(frame_json)
    
    adjust_data = json.loads(image_adjust)
    print(f"ADJUSTMENTS (from image_adjust Form field): {adjust_data}")
    # Note: frontend sends it as 'image_adjust', not inside 'frame_json.adjustments'
    
    fg_path = f"tmp/{id}_fg.png"
    if not os.path.exists(fg_path):
        raise HTTPException(status_code=404, detail="Image not found")
        
    face_nobg = Image.open(fg_path).convert("RGBA")
    
    # Parse JSON strings
    frame_data = json.loads(frame_json)
    adjust_data = json.loads(image_adjust)
    text_info = json.loads(text_data)
    
    template_w, template_h = template_img.size if template_img else (3000, 4000)
    mapped_frame = map_frame(frame_data, template_w, template_h)
    
    # Shift to main_frame local coordinates
    mapped_frame["x"] -= config["main_frame"]["x"]
    mapped_frame["y"] -= config["main_frame"]["y"]
    
    # Save debug info
    os.makedirs("outputs/debug", exist_ok=True)
    with open("outputs/debug/frame_received.json", "w", encoding="utf-8") as f:
        json.dump(frame_data, f, indent=2)
        
    with open("outputs/debug/frame_render.json", "w", encoding="utf-8") as f:
        json.dump(mapped_frame, f, indent=2)
        
    with open("outputs/debug/final_position.txt", "w", encoding="utf-8") as f:
        f.write(f"x:\n{mapped_frame['x']}\n")
        f.write(f"y:\n{mapped_frame['y']}\n")
        f.write(f"scale:\n{mapped_frame['scale']}\n")
        f.write(f"width:\n{mapped_frame['width']}\n")
        f.write(f"height:\n{mapped_frame['height']}\n")
    
    target_w = config["main_frame"]["width"]
    target_h = config["main_frame"]["height"]
    
    # Apply frame and render
    framed_canvas = apply_frame(face_nobg, target_w, target_h, mapped_frame)
    
    card = render_final_card(framed_canvas, template_img, config, adjust_data, 
                             pic2_bg, holo_img, text_data=text_info, fonts=fonts, is_preview=False)
                             
    out_path = f"outputs/{id}_final.png"
    card.convert("RGB").save(out_path, "PNG")
    
    import time
    return {
        "output_url": f"http://localhost:8000/outputs/{id}_final.png?t={int(time.time() * 1000)}",
        "frame_used": mapped_frame
    }

def process_single_image(img_bgr, out_path, adjust_data=None):
    region = detect_face_multi_stage(img_bgr)
    if not region:
        region = {'x': 0, 'y': 0, 'w': img_bgr.shape[1], 'h': img_bgr.shape[0]}
        
    face_nobg = remove_background(img_bgr)
    
    target_w = config["main_frame"]["width"]
    target_h = config["main_frame"]["height"]
    
    orig_w, orig_h = face_nobg.size
    target_fg_h = target_h * 0.92
    scale = target_fg_h / orig_h
    
    face_top_scaled = region['y'] * scale
    y_offset = target_h * 0.12 - face_top_scaled
    
    face_center_x_scaled = (region['x'] + region['w'] / 2.0) * scale
    x_offset = (target_w / 2.0) - face_center_x_scaled
    
    mapped_frame = {
        "x": x_offset,
        "y": y_offset,
        "scale": scale,
        "rotation": 0,
        "width": orig_w * scale,
        "height": orig_h * scale,
        "canvas_width": target_w,
        "canvas_height": target_h
    }
    
    framed_canvas = apply_frame(face_nobg, target_w, target_h, mapped_frame)
    
    if adjust_data is None:
        adjust_data = {
            "brightness": 1.05,
            "contrast": 1.08,
            "saturation": 1.10
        }
    
    text_info = {
        "id_num": "0123456789",
        "last_name": "NGUYEN",
        "first_name": "VAN A",
        "middle_name": "THI",
        "dob": "01/01/1990",
        "address": "123 Auto Gen Street"
    }
    
    card = render_final_card(framed_canvas, template_img, config, adjust_data, 
                             pic2_bg, holo_img, text_data=text_info, fonts=fonts, is_preview=False)
                             
    card.convert("RGB").save(out_path, "PNG")


@app.post("/api/auto_preview")
async def auto_preview(
    image: UploadFile = File(...),
    adjustments: str = Form("{}")
):
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Invalid image")
        
    adjust_data = json.loads(adjustments)
    img_id = str(uuid.uuid4())
    out_path = f"tmp/{img_id}_preview.png"
    
    # Process synchronously for preview
    process_single_image(img_bgr, out_path, adjust_data)
    
    import time
    return {
        "preview_url": f"http://localhost:8000/tmp/{img_id}_preview.png?t={int(time.time() * 1000)}"
    }

@app.get("/api/batch_progress/{batch_id}")
async def get_batch_progress(batch_id: str):
    bc = batch_registry.get(batch_id)
    if not bc:
        return {"current": 0, "total": 0, "status": "unknown", "percent": 0}
    with bc.lock:
        return dict(bc.progress)

@app.get("/api/batch_results/{batch_id}")
async def get_batch_results(batch_id: str):
    bc = batch_registry.get(batch_id)
    if not bc:
        raise HTTPException(status_code=404, detail="Batch not found")
        
    files = []
    if os.path.exists(bc.output_dir):
        for filename in os.listdir(bc.output_dir):
            if filename.startswith("img_") and filename.endswith(".png"):
                files.append(f"http://localhost:8000/{bc.output_dir}/{filename}")
                
    return {
        "files": sorted(files),
        "output_folder": f"http://localhost:8000/{bc.output_dir}/",
        "zip_url": f"http://localhost:8000/api/download_batch/{batch_id}"
    }

async def run_batch(batch_context: BatchContext, input_files: List[str], adjust_data: dict = None):
    total = len(input_files)
    with batch_context.lock:
        batch_context.progress["total"] = total
        batch_context.progress["status"] = "processing"
    
    pad_width = len(str(total))
    
    for i, file_path in enumerate(input_files):
        filename = f"img_{i+1:0{pad_width}d}.png"
        out_path = f"{batch_context.output_dir}/{filename}"
        
        # Enforce output isolation rule
        assert out_path.startswith(batch_context.output_dir)
        
        try:
            img_bgr = cv2.imread(file_path)
            if img_bgr is not None:
                await asyncio.to_thread(process_single_image, img_bgr, out_path, adjust_data)
        except Exception as e:
            error_msg = f"Error processing image {i}: {e}\n"
            print(error_msg)
            with open(f"{batch_context.output_dir}/errors.log", "a", encoding="utf-8") as f:
                f.write(error_msg)
        finally:
            if 'img_bgr' in locals() and img_bgr is not None:
                del img_bgr
            gc.collect()
            
            # Clean up the input file to save disk space
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            
        with batch_context.lock:
            batch_context.progress["current"] = i + 1
            batch_context.progress["percent"] = int(((i + 1) / total) * 100) if total > 0 else 0
            
    with batch_context.lock:
        batch_context.progress["status"] = "completed"
        batch_context.progress["percent"] = 100
        
    shutil.make_archive(batch_context.output_dir, 'zip', batch_context.output_dir)

@app.post("/api/batch_generate")
async def batch_generate(
    background_tasks: BackgroundTasks,
    batch_id: str = Form(...),
    adjustments: str = Form("{}"),
    images: Optional[List[UploadFile]] = File(None),
    zip_file: UploadFile = File(None)
):
    batch_context = BatchContext(batch_id)
    batch_registry[batch_id] = batch_context
    adjust_data = json.loads(adjustments)
    
    os.makedirs(batch_context.output_dir, exist_ok=True)
    input_dir = os.path.join(batch_context.output_dir, "inputs")
    os.makedirs(input_dir, exist_ok=True)
    
    input_files = []
    
    if zip_file and zip_file.filename:
        contents = await zip_file.read()
        try:
            with zipfile.ZipFile(io.BytesIO(contents)) as z:
                for filename in z.namelist():
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        # Save directly to disk
                        out_file = os.path.join(input_dir, os.path.basename(filename))
                        with z.open(filename) as source, open(out_file, "wb") as target:
                            shutil.copyfileobj(source, target)
                        input_files.append(out_file)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
            
    if images:
        for img_file in images:
            if img_file.filename:
                contents = await img_file.read()
                out_file = os.path.join(input_dir, os.path.basename(img_file.filename))
                with open(out_file, "wb") as f:
                    f.write(contents)
                input_files.append(out_file)
                
    total = len(input_files)
    if total == 0:
        raise HTTPException(status_code=400, detail="No valid images found")
        
    background_tasks.add_task(run_batch, batch_context, input_files, adjust_data)
    
    return {
        "success": True,
        "batch_id": batch_id,
        "total": total,
        "status": "started"
    }

@app.get("/api/download_batch/{batch_id}")
async def download_batch(batch_id: str):
    zip_path = f"outputs/batch_{batch_id}.zip"
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Batch ZIP not found")
    return FileResponse(zip_path, media_type="application/zip", filename=f"batch_{batch_id}.zip")

@app.post("/api/save_frame")
async def save_frame(req: SaveFrameRequest):
    with open("outputs/frame.json", "w", encoding="utf-8") as f:
        json.dump(req.frame, f, indent=2)
    return {"status": "OK", "message": "Frame saved successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
