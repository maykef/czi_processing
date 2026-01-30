#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import numpy as np
import zarr
import dask.array as da
import napari

# --- MICROSCOPE SPECS ---
XY_RES = 0.65  # microns per pixel
Z_RES = 2.0    # microns per slice
# Z is ~3.08x larger than X/Y
Z_STRETCH = Z_RES / XY_RES

def main():
    parser = argparse.ArgumentParser(description="High-Performance Napari Zarr Viewer")
    parser.add_argument("zarr_path", help="Path to the .zarr folder")
    args = parser.parse_args()

    z_path = Path(args.zarr_path)
    if not z_path.exists():
        print(f"Error: {z_path} not found.")
        return

    # Load multiscale levels (0=Full, 1=1/2, 2=1/4, etc.) 
    levels = []
    for i in range(5):
        p = z_path / str(i)
        if p.exists():
            levels.append(da.from_zarr(str(p)))

    viewer = napari.Viewer(title=f"Viewing: {z_path.name}")
    
    # Napari scale for Image Layers is (Z, Y, X)
    # We leave Y and X at 1.0 and stretch Z
    voxel_scale = [Z_STRETCH, 1.0, 1.0]

    # Add each channel as a separate layer for independent control
    n_channels = levels[0].shape[0]
    for c in range(n_channels):
        # Create a list of dask arrays for this specific channel across all scales
        multiscale_channel = [level[c] for level in levels]
        
        viewer.add_image(
            multiscale_channel,
            name=f"Channel {c}",
            multiscale=True,
            scale=voxel_scale, # This prevents the 'flattened' look
            blending='additive',
            rendering='mip', # Maximum Intensity Projection for 3D
            colormap='green' if c == 0 else 'magenta'
        )

    print(f"Launched Napari with Z-Axis stretch of {Z_STRETCH:.2f}")
    napari.run()

if __name__ == "__main__":
    main()
