#!/usr/bin/env python3
import sys
from pathlib import Path
import numpy as np
import zarr
import dask.array as da
import napari

def main():
    # ==================== CONFIGURATION ====================
    ZARR_PATH = "TY-Dip_2.1.1.zarr"
    # =======================================================
    
    script_dir = Path(__file__).resolve().parent
    zarr_path = script_dir / ZARR_PATH
    
    if not zarr_path.exists():
        print(f"ERROR: {zarr_path} does not exist")
        return 1
    
    print(f"Opening ZARR: {zarr_path}")
    
    # 1. Attempt to load as a multiscale pyramid
    # Common Zarr structures use '0', '1', '2' for downsampled levels
    levels = ['0', '1', '2', '3', '4']
    multiscale_data = []
    
    for level in levels:
        p = zarr_path / level
        if p.exists():
            # Load each level as a lazy dask array
            multiscale_data.append(da.from_zarr(str(p)))
            print(f"Found resolution level {level}: {multiscale_data[-1].shape}")

    if not multiscale_data:
        print("ERROR: No data levels (e.g., '0/') found in Zarr.")
        return 1

    # 2. Setup Viewer
    viewer = napari.Viewer()
    
    # 3. Add Channels
    # We assume all levels have the same number of channels (Axis 0)
    n_channels = multiscale_data[0].shape[0]
    
    for c in range(n_channels):
        # Create a list of the specific channel for all available scales
        channel_layers = [level[c] for level in multiscale_data]
        
        # Calculate contrast limits using a mid-resolution level if available
        # This prevents loading the massive level '0' just for a preview
        calc_level = min(len(channel_layers) - 1, 2) 
        sample_data = channel_layers[calc_level]
        
        print(f"Calculating contrast for Channel {c} using level {calc_level}...")
        sample_slice = sample_data[sample_data.shape[0]//2].compute()
        p1, p99 = np.percentile(sample_slice, [1, 99.9])

        viewer.add_image(
            channel_layers,
            name=f"Channel_{c}",
            multiscale=True,
            colormap='green' if c == 0 else 'magenta',
            contrast_limits=[float(p1), float(p99)],
            blending='additive'
        )
    
    print("\nSUCCESS: Use the '3D' button in the bottom left.")
    print("If it still hangs, your Zarr likely lacks downsampled levels ('1', '2', etc.).")
    
    napari.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
