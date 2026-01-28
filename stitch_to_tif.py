#!/usr/bin/env python3
"""
CZI Parallel Stitcher - Memory-Aware Version
============================================
Uses multiprocessing with conservative worker count
Memory usage: ~850 MB per worker at peak
"""

import sys
import time
from pathlib import Path
import numpy as np
from aicspylibczi import CziFile
from tifffile import imwrite
from multiprocessing import Pool, cpu_count

def create_linear_blend_weights(h, w, blend_pixels=80):
    """Create blending weights with linear falloff at edges"""
    weights = np.ones((h, w), dtype=np.float32)
    
    for i in range(blend_pixels):
        alpha = i / blend_pixels
        weights[i, :] = alpha
        weights[-(i+1), :] = alpha
        weights[:, i] = np.minimum(weights[:, i], alpha)
        weights[:, -(i+1)] = np.minimum(weights[:, -(i+1)], alpha)
    
    return weights

def stitch_single_plane(args):
    """Worker function - stitches one plane"""
    czi_path, z, c, output_dir = args
    
    try:
        czi = CziFile(str(czi_path))
        tile_bboxes = czi.get_all_mosaic_tile_bounding_boxes(Z=z, C=c)
        
        if not tile_bboxes:
            return (z, c, False, "No tiles")
        
        # Canvas size
        min_x = min(bbox.x for bbox in tile_bboxes.values())
        min_y = min(bbox.y for bbox in tile_bboxes.values())
        max_x = max(bbox.x + bbox.w for bbox in tile_bboxes.values())
        max_y = max(bbox.y + bbox.h for bbox in tile_bboxes.values())
        
        canvas_w = max_x - min_x
        canvas_h = max_y - min_y
        
        # Accumulators
        canvas = np.zeros((canvas_h, canvas_w), dtype=np.float64)
        weights_sum = np.zeros((canvas_h, canvas_w), dtype=np.float32)
        
        # Process tiles
        for tile_info, bbox in tile_bboxes.items():
            try:
                tile_img, _ = czi.read_image(Z=z, C=c, M=tile_info.m_index)
                
                while tile_img.ndim > 2 and tile_img.shape[0] == 1:
                    tile_img = tile_img[0]
                
                x_start = bbox.x - min_x
                y_start = bbox.y - min_y
                x_end = x_start + bbox.w
                y_end = y_start + bbox.h
                
                if x_end > canvas_w or y_end > canvas_h:
                    continue
                
                tile_weights = create_linear_blend_weights(bbox.h, bbox.w, blend_pixels=80)
                
                canvas[y_start:y_end, x_start:x_end] += tile_img.astype(np.float64) * tile_weights
                weights_sum[y_start:y_end, x_start:x_end] += tile_weights
                
            except Exception:
                continue
        
        # Normalize
        mask = weights_sum > 0
        canvas[mask] /= weights_sum[mask]
        result = np.clip(canvas, 0, 65535).astype(np.uint16)
        
        # Save
        output_path = output_dir / f"C{c}_Z{z:04d}.tif"
        imwrite(output_path, result, compression='zlib', compressionargs={'level': 6})
        
        return (z, c, True, None)
        
    except Exception as e:
        return (z, c, False, str(e))

def main():
    # ==================== CONFIGURATION ====================
    CZI_FILENAME = "TY_Dip_2.1.1_Z1_Veh_488_638_Whole.czi"
    # CZI_FILENAME = "TY_Dip_2.1.1_Z1_Veh_488_638_Whole.czi"
    
    OUTPUT_DIR_NAME = "TY_Dip_2.1.1"
    N_WORKERS = 28  # Increased from 16. Peak memory: ~24GB
                    # Your system: 32 cores, 122GB RAM - plenty of capacity
    # =======================================================
    
    script_dir = Path(__file__).resolve().parent
    czi_path = script_dir / CZI_FILENAME
    
    if not czi_path.exists():
        print(f"ERROR: {czi_path} not found")
        print(f"Available: {[f.name for f in script_dir.glob('*.czi')]}")
        return 1
    
    print(f"CZI: {czi_path.name}")
    print(f"Workers: {N_WORKERS} of {cpu_count()} CPUs")
    print(f"Memory: ~{N_WORKERS * 0.85:.1f} GB peak usage\n")
    
    # Get dimensions
    czi = CziFile(str(czi_path))
    dims = czi.get_dims_shape()[0]
    n_z = dims['Z'][1]
    n_c = dims['C'][1]
    total = n_z * n_c
    
    print(f"Dataset: {n_z} Z × {n_c} C = {total} planes\n")
    
    # Output directory
    output_dir = script_dir / OUTPUT_DIR_NAME
    output_dir.mkdir(exist_ok=True)
    
    # Build task list
    tasks = [(czi_path, z, c, output_dir) for c in range(n_c) for z in range(n_z)]
    
    print("Starting parallel processing...")
    start_time = time.time()
    completed = 0
    failed = 0
    
    # Process with pool
    with Pool(processes=N_WORKERS) as pool:
        for result in pool.imap_unordered(stitch_single_plane, tasks):
            z, c, success, error = result
            completed += 1
            
            if not success:
                failed += 1
                if failed <= 3:
                    print(f"  Failed C{c} Z{z:04d}: {error}")
            
            # Progress every 50 planes
            if completed % 50 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                eta_min = (total - completed) / rate / 60 if rate > 0 else 0
                
                print(f"[{completed}/{total}] {rate:.1f} pl/s | ETA {eta_min:.1f} min | Failed {failed}")
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Complete: {completed - failed}/{total} planes in {elapsed/60:.1f} min")
    print(f"Rate: {completed/elapsed:.1f} planes/second")
    print(f"Failed: {failed}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
