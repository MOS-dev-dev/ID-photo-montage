import os
import glob
import shutil

SOURCE_DIRS = ['anh_nam_tre', 'anh_nam_gia', 'anh_nu_tre', 'anh_nu_gia']
TARGET_DIR = 'golden_dataset'
COUNT = 100

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    src_files = []
    for d in SOURCE_DIRS:
        if os.path.exists(d):
            src_files.extend(glob.glob(os.path.join(d, '*.*')))
            
    # Filter for images
    src_files = [f for f in src_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    # Sort to ensure reproducibility
    src_files.sort()
    
    if not src_files:
        print("No source files found.")
        return
        
    print(f"Generating {COUNT} golden images without augmentation...")
    
    for i in range(COUNT):
        src = src_files[i % len(src_files)]
        dst = os.path.join(TARGET_DIR, f"golden_{i:03d}.jpg")
        shutil.copy(src, dst)
        
    print(f"Successfully generated {COUNT} files in {TARGET_DIR}.")

if __name__ == "__main__":
    main()
