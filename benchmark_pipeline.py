import os
import sys
import glob
from tool_tao_the import process_portrait, DEBUG_DIR

def run_benchmark():
    folders = ['anh_nam_tre', 'anh_nam_gia', 'anh_nu_tre', 'anh_nu_gia']
    total_processed = 0
    total_passed = 0
    total_failed = 0
    
    # Track reframing stats
    reframe_stats = {1: 0, 2: 0, 3: 0, 4: 0}
    
    print("="*50)
    print(" BẮT ĐẦU CHẠY BENCHMARK 400 ẢNH (V3: ADAPTIVE REFRAMING)")
    print("="*50)
    
    # Clear old debug images
    if os.path.exists(DEBUG_DIR):
        for f in glob.glob(f"{DEBUG_DIR}/*"):
            try: os.remove(f)
            except: pass
            
    for folder in folders:
        print(f"\n[{folder.upper()}] Đang kiểm tra...")
        if not os.path.exists(folder):
            print(f"  -> Thư mục không tồn tại: {folder}")
            continue
            
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        # Lấy tối đa 100 ảnh
        files = files[:100]
        
        folder_processed = len(files)
        folder_passed = 0
        folder_failed = 0
        
        for idx, file in enumerate(files):
            file_path = os.path.join(folder, file)
            # Lưu 5 mẫu debug đầu tiên của mỗi category
            debug_id = f"bench_{folder}_{idx:03d}" if idx < 5 else None
            try:
                main_p, ghost_p, reframes = process_portrait(file_path, debug_id=debug_id)
                if main_p is not None:
                    folder_passed += 1
                    reframe_stats[reframes] = reframe_stats.get(reframes, 0) + 1
                else:
                    folder_failed += 1
            except Exception as e:
                print(f"  Lỗi khi xử lý {file}: {e}")
                folder_failed += 1
                
        total_processed += folder_processed
        total_passed += folder_passed
        total_failed += folder_failed
        
        if folder_processed > 0:
            pass_rate = (folder_passed / folder_processed) * 100
        else:
            pass_rate = 0.0
            
        print(f"  -> Processed: {folder_processed}, Passed: {folder_passed}, Failed: {folder_failed}")
        print(f"  -> Pass Rate: {pass_rate:.2f}%")
        
    print("\n" + "="*50)
    print(" KẾT QUẢ BENCHMARK TỔNG THỂ V3")
    print("="*50)
    print(f" Total Processed: {total_processed}")
    print(f" Total Passed:    {total_passed}")
    print(f" Total Failed:    {total_failed}")
    if total_processed > 0:
        print(f" OVERALL RATE:    {(total_passed / total_processed) * 100:.2f}%")
        
    print("\n Chi tiết Auto Reframing:")
    for k, v in reframe_stats.items():
        print(f"  - Sử dụng Attempt #{k}: {v} ảnh")
    print("="*50)

if __name__ == "__main__":
    run_benchmark()
