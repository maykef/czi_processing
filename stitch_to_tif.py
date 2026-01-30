#!/usr/bin/env python3
"""
CZI Parallel Stitcher - Hardware Overdrive Version
==================================================
Optimized for 32-core Threadripper + PCIe 5.0 NVMe.
"""

import sys
import time
import argparse
import warnings
from pathlib import Path
import numpy as np
from aicspylibczi import CziFile
from tifffile import imwrite
from multiprocessing import Pool, cpu_count
from functools import lru_cache

# Silence redundant image warnings
warnings.filterwarnings("ignore")

@lru_cache(maxsize=32)
def get_cached_weights(h, w, blend_pixels=80):
    """Optimization: Cache blending weights to avoid redundant calculations."""
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
    czi_path, z, c, output_dir, blend_px = args
    try:
        czi = CziFile(str(czi_path))
        tile_bboxes = czi.get_all_mosaic_tile_bounding_boxes(Z=z, C=c)
        if not tile_bboxes: return (z, c, False, "No tiles")

        min_x = min(bbox.x for bbox in tile_bboxes.values())
        min_y = min(bbox.y for bbox in tile_bboxes.values())
        max_x = max(bbox.x + bbox.w for bbox in tile_bboxes.values())
        max_y = max(bbox.y + bbox.h for bbox in tile_bboxes.values())
        
        canvas_w, canvas_h = max_x - min_x, max_y - min_y
        canvas = np.zeros((canvas_h, canvas_w), dtype=np.float32)
        weights_sum = np.zeros((canvas_h, canvas_w), dtype=np.float32)
        
        for tile_info, bbox in tile_bboxes.items():
            tile_img, _ = czi.read_image(Z=z, C=c, M=tile_info.m_index)
            tile_img = np.squeeze(tile_img)
            x_s, y_s = bbox.x - min_x, bbox.y - min_y
            
            tile_weights = get_cached_weights(bbox.h, bbox.w, blend_px)
            canvas[y_s:y_s+bbox.h, x_s:x_s+bbox.w] += tile_img.astype(np.float32) * tile_weights
            weights_sum[y_s:y_s+bbox.h, x_s:x_s+bbox.w] += tile_weights
        
        mask = weights_sum > 0
        canvas[mask] /= weights_sum[mask]
        result = np.clip(canvas, 0, 65535).astype(np.uint16)
        
        output_path = output_dir / f"C{c}_Z{z:04d}.tif"
        imwrite(output_path, result, compression='zlib', compressionargs={'level': 1})
        return (z, c, True, None)
    except Exception as e:
        return (z, c, False, str(e))

def main():
    parser = argparse.ArgumentParser(description="Overdrive CZI Stitcher")
    parser.add_argument("input_czi", help="Input .czi file")
    parser.add_argument("output_dir", help="Output directory for TIFFs")
    args = parser.parse_args()

    N_WORKERS = 48 # Optimal for 128GB RAM
    BLEND_PIXELS = 80
    
    script_dir = Path(__file__).resolve().parent
    czi_path = script_dir / args.input_czi
    output_dir = script_dir / args.output_dir
    output_dir.mkdir(exist_ok=True)
    
    czi = CziFile(str(czi_path))
    dims = czi.get_dims_shape()[0]
    n_z, n_c = dims['Z'][1], dims['C'][1]
    total = n_z * n_c
    
    tasks = [(czi_path, z, c, output_dir, BLEND_PIXELS) for c in range(n_c) for z in range(n_z)]
    
    print(f"Starting Overdrive Stitcher: {N_WORKERS} Workers")
    start_time = time.time()
    
    with Pool(processes=N_WORKERS) as pool:
        completed = 0
        for result in pool.imap_unordered(stitch_single_plane, tasks):
            completed += 1
            if completed % 100 == 0 or completed == total:
                rate = completed / (time.time() - start_time)
                print(f"Progress: [{completed}/{total}] | Rate: {rate:.1f} pl/s")

    print(f"Stitching complete in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    main()
