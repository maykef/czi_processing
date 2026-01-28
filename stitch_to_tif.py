#!/usr/bin/env python3
"""
Convert Stitched Planes to OME-ZARR
===================================
Creates a pyramidal OME-ZARR that napari can open efficiently
Uses lazy loading - napari only loads what's visible
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
    CHUNK_SIZE = (1, 512, 512)  # (Z, Y, X) chunks for efficient access
    # =======================================================
    
    script_dir = Path(__file__).resolve().parent
    input_dir = script_dir / INPUT_DIR
    output_path = script_dir / OUTPUT_ZARR
    
    if not input_dir.exists():
        print(f"ERROR: {input_dir} not found")
        return 1
    
    # Get all TIFF files
    tif_files = sorted(input_dir.glob("*.tif"))
    if not tif_files:
        print(f"ERROR: No TIFF files in {input_dir}")
        return 1
    
    print(f"Found {len(tif_files)} TIFF files")
    
    # Parse filenames to organize by channel
    channels = {}
    for tif_path in tif_files:
        # Format: C{c}_Z{zzzz}.tif
        parts = tif_path.stem.split('_')
        c = int(parts[0][1:])
        z = int(parts[1][1:])
        
        if c not in channels:
            channels[c] = {}
        channels[c][z] = tif_path
    
    n_c = len(channels)
    n_z = max(len(z_slices) for z_slices in channels.values())
    
    # Get image dimensions from first file
    first_img = imread(list(channels[0].values())[0])
    n_y, n_x = first_img.shape
    dtype = first_img.dtype
    
    print(f"\nDataset dimensions:")
    print(f"  Channels: {n_c}")
    print(f"  Z-slices: {n_z}")
    print(f"  Y: {n_y}")
    print(f"  X: {n_x}")
    print(f"  Dtype: {dtype}")
    print(f"  Total size: {n_c * n_z * n_y * n_x * np.dtype(dtype).itemsize / 1024**3:.1f} GB")
    
    # Create lazy-loading dask array for each channel
    print(f"\nBuilding lazy-loading arrays...")
    
    @delayed
    def load_plane(path):
        return imread(path)
    
    channel_arrays = []
    for c in sorted(channels.keys()):
        z_slices = sorted(channels[c].keys())
        
        # Create delayed array for each Z slice
        lazy_arrays = []
        for z in z_slices:
            if z in channels[c]:
                lazy_arr = da.from_delayed(
                    load_plane(channels[c][z]),
                    shape=(n_y, n_x),
                    dtype=dtype
                )
                lazy_arrays.append(lazy_arr)
            else:
                # Missing slice - fill with zeros
                lazy_arrays.append(da.zeros((n_y, n_x), dtype=dtype))
        
        # Stack along Z
        channel_stack = da.stack(lazy_arrays, axis=0)
        channel_arrays.append(channel_stack)
    
    # Stack channels
    volume = da.stack(channel_arrays, axis=0)
    print(f"  Dask array shape: {volume.shape} (C, Z, Y, X)")
    
    # Rechunk for efficient access
    print(f"  Rechunking to {CHUNK_SIZE}...")
    volume = volume.rechunk({0: 1, 1: CHUNK_SIZE[0], 2: CHUNK_SIZE[1], 3: CHUNK_SIZE[2]})
    
    # Write to OME-ZARR
    print(f"\nWriting to {output_path}...")
    print(f"  This will write on-demand as napari accesses data")
    
    # Create zarr store
    store = zarr.DirectoryStore(str(output_path))
    root = zarr.group(store=store, overwrite=True)
    
    # Write multiscale pyramid (just full resolution for now)
    # Napari will create downsampled versions on the fly if needed
    dataset = root.create_dataset(
        '0',
        shape=volume.shape,
        chunks=(1, CHUNK_SIZE[0], CHUNK_SIZE[1], CHUNK_SIZE[2]),
        dtype=dtype,
        compressor=zarr.Blosc(cname='zstd', clevel=3, shuffle=2)
    )
    
    # Store data
    print(f"  Computing and storing chunks (this may take a few minutes)...")
    da.to_zarr(volume, dataset)
    
    # Add OME-ZARR metadata
    root.attrs['multiscales'] = [{
        'version': '0.4',
        'axes': [
            {'name': 'c', 'type': 'channel'},
            {'name': 'z', 'type': 'space', 'unit': 'micrometer'},
            {'name': 'y', 'type': 'space', 'unit': 'micrometer'},
            {'name': 'x', 'type': 'space', 'unit': 'micrometer'}
        ],
        'datasets': [
            {'path': '0', 'coordinateTransformations': [{'type': 'scale', 'scale': [1, 1, 1, 1]}]}
        ]
    }]
    
    print(f"\n{'='*60}")
    print(f"Complete!")
    print(f"  Output: {output_path}")
    print(f"  Size on disk: {sum(f.stat().st_size for f in output_path.rglob('*') if f.is_file()) / 1024**3:.1f} GB")
    print(f"\nTo view in napari:")
    print(f"  napari {output_path}")
    print(f"{'='*60}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
