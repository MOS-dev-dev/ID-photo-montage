import os
import sys
import json
import glob
from tool_tao_the import process_portrait

EXTERNAL_DS_PATH = 'external_dataset'

def run_external_validation():
    print("\n[EXTERNAL VALIDATION] Running on 100 completely new images...")
    
    total, passed, failed = 0, 0, 0
    files = glob.glob(os.path.join(EXTERNAL_DS_PATH, '*.jpg'))
    
    for f in files:
        total += 1
        try:
            main_p, ghost_p, reframes, _ = process_portrait(f)
            if main_p is not None:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    report = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate
    }
    
    with open('external_validation_report.json', 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"External Validation Complete: Pass Rate = {pass_rate:.2f}%")

if __name__ == "__main__":
    run_external_validation()
