#!/usr/bin/env python3
"""
Convert Stitched Planes to Pyramidal OME-ZARR
============================================
Optimized for 3D viewing. Overwrites previous incomplete Zarrs.
"""

import sys
from pathlib import Path
import numpy as np
import zarr
from tifffile import imread
import dask.array as da
from dask import delayed

def main():
    # ==================== CONFIGURATION ====================
    INPUT_DIR = "TY_Dip_2.1.1"
    OUTPUT_ZARR = "TY-Dip_2.1.1.zarr"
    
    # CHUNKS: 32 slices deep in Z allows Napari to "see" through the volume
    CHUNK_SIZE = (1, 32, 256, 256) 
    LEVELS = 4  
    
    # VOXEL SIZE: Change these to your actual microscope specs (Z, Y, X)
    # This prevents the 3D volume from looking flattened.
    VOXEL_SIZE = [2.0, 1.0, 1.0] 
    # =======================================================
    
    script_dir = Path(__file__).resolve().parent
    input_dir = script_dir / INPUT_DIR
    output_path = script_dir / OUTPUT_ZARR
    
    if not input_dir.exists():
        print(f"ERROR: {input_dir} not found")
        return 1
    
    # 1. ORGANIZE FILES
    tif_files = sorted(input_dir.glob("*.tif"))
    if not tif_files:
        print(f"ERROR: No TIFF files in {input_dir}")
        return 1
    
    channels = {}
    for tif_path in tif_files:
        parts = tif_path.stem.split('_')
        c = int(parts[0][1:])
        z = int(parts[1][1:])
        if c not in channels: channels[c] = {}
        channels[c][z] = tif_path
    
    n_c = len(channels)
    n_z = max(len(z_slices) for z_slices in channels.values())
    first_img = imread(list(channels[0].values())[0])
    n_y, n_x = first_img.shape
    dtype = first_img.dtype
    
    print(f"Dataset: {n_c}C, {n_z}Z, {n_y}Y, {n_x}X | Dtype: {dtype}")

    # 2. BUILD LAZY DASK STACK
    @delayed
    def load_plane(path):
        return imread(path)
    
    channel_stacks = []
    for c in sorted(channels.keys()):
        z_slices = [channels[c].get(z) for z in range(n_z)]
        lazy_planes = [
            da.from_delayed(load_plane(p), shape=(n_y, n_x), dtype=dtype) if p 
            else da.zeros((n_y, n_x), dtype=dtype) 
            for p in z_slices
        ]
        channel_stacks.append(da.stack(lazy_planes, axis=0))
    
    volume = da.stack(channel_stacks, axis=0).rechunk(CHUNK_SIZE)

    # 3. WRITE PYRAMID LEVELS
    # This will overwrite the existing Zarr structure
    store = zarr.DirectoryStore(str(output_path))
    root = zarr.group(store=store, overwrite=True)
    multiscales_metadata = []
    
    current_vol = volume
    
    for level in range(LEVELS):
        level_path = str(level)
        print(f"\nWriting Level {level} | Shape: {current_vol.shape}")
        
        da.to_zarr(
            current_vol, 
            store, 
            component=level_path, 
            overwrite=True,
            compressor=zarr.Blosc(cname='zstd', clevel=3, shuffle=2)
        )
        
        # Calculate scaling for this level
        s = 2**level
        # Scale for [C, Z, Y, X]
        current_scale = [1.0, VOXEL_SIZE[0]*s, VOXEL_SIZE[1]*s, VOXEL_SIZE[2]*s]
        
        multiscales_metadata.append({
            "path": level_path,
            "coordinateTransformations": [{"type": "scale", "scale": current_scale}]
        })
        
        if level < LEVELS - 1:
            # Downsample for next iteration
            current_vol = da.coarsen(np.mean, current_vol, {1: 2, 2: 2, 3: 2}, trim_excess=True).astype(dtype)

    # 4. OME-ZARR METADATA
    root.attrs['multiscales'] = [{
        'version': '0.4',
        'axes': [
            {'name': 'c', 'type': 'channel'},
            {'name': 'z', 'type': 'space', 'unit': 'micrometer'},
            {'name': 'y', 'type': 'space', 'unit': 'micrometer'},
            {'name': 'x', 'type': 'space', 'unit': 'micrometer'}
        ],
        'datasets': multiscales_metadata
    }]
    
    print(f"\nDone! Overwrote {output_path} with a full 3D pyramid.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
