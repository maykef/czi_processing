#!/usr/bin/env python3
"""
Convert Stitched Planes to Pyramidal OME-ZARR (Hardware Overdrive)
"""

import sys
import time
import argparse
import warnings
from pathlib import Path
import numpy as np
import zarr
import numcodecs
from tifffile import imread
import dask.array as da
from dask import delayed
from dask.diagnostics import ProgressBar

warnings.filterwarnings("ignore")

def main():
    parser = argparse.ArgumentParser(description="Overdrive Zarr Converter")
    parser.add_argument("input_dir", help="Directory containing the stitched TIFFs")
    parser.add_argument("output_zarr", help="Name of the output .zarr file")
    args = parser.parse_args()

    CHUNK_SIZE = (1, 64, 512, 512) 
    LEVELS = 4  
    VOXEL_SIZE = [2.0, 1.0, 1.0] 
    
    script_dir = Path(__file__).resolve().parent
    input_dir = script_dir / args.input_dir
    output_path = script_dir / args.output_zarr
    
    tif_files = sorted(input_dir.glob("*.tif"))
    channels = {}
    for tif_path in tif_files:
        parts = tif_path.stem.split('_')
        c, z = int(parts[0][1:]), int(parts[1][1:])
        if c not in channels: channels[c] = {}
        channels[c][z] = tif_path
    
    n_c, n_z = len(channels), max(len(z_slices) for z_slices in channels.values())
    first_img = imread(list(channels[0].values())[0])
    dtype = first_img.dtype
    
    @delayed
    def load_plane(path): return imread(path)
    
    channel_stacks = []
    for c in sorted(channels.keys()):
        z_slices = [channels[c].get(z) for z in range(n_z)]
        lazy_planes = [da.from_delayed(load_plane(p), shape=first_img.shape, dtype=dtype) if p 
                       else da.zeros(first_img.shape, dtype=dtype) for p in z_slices]
        channel_stacks.append(da.stack(lazy_planes, axis=0))
    
    volume = da.stack(channel_stacks, axis=0).rechunk(CHUNK_SIZE)
    root = zarr.open_group(str(output_path), mode='w')
    multiscales_metadata = []
    blosc_compressor = numcodecs.Blosc(cname='zstd', clevel=3, shuffle=numcodecs.Blosc.BITSHUFFLE)
    
    start_time = time.time()
    current_vol = volume
    for level in range(LEVELS):
        level_path = str(level)
        print(f"\nProcessing Level {level} {current_vol.shape}...")
        with ProgressBar():
            da.to_zarr(current_vol, str(output_path), component=level_path, overwrite=True, compressor=blosc_compressor)
        
        s = 2**level
        multiscales_metadata.append({"path": level_path, "coordinateTransformations": [{"type": "scale", "scale": [1.0, VOXEL_SIZE[0]*s, VOXEL_SIZE[1]*s, VOXEL_SIZE[2]*s]}]})
        if level < LEVELS - 1:
            current_vol = da.coarsen(np.mean, current_vol, {1: 2, 2: 2, 3: 2}, trim_excess=True).astype(dtype)

    root.attrs['multiscales'] = [{'version': '0.4', 'datasets': multiscales_metadata}]
    print(f"\nConversion Complete in {(time.time() - start_time)/60:.2f}m")

if __name__ == "__main__":
    main()
