#!/usr/bin/env python3
import sys
from pathlib import Path
import numpy as np
import zarr
import dask.array as da
import dask
from dask.cache import Cache
import napari
from magicgui import magicgui

# ==================== RAM OPTIMIZATION ====================
# Using ~40GB of your 128GB for data caching
cache = Cache(40e9) 
cache.register()
# Prevent dask from being too aggressive with memory splitting
dask.config.set({'array.slicing.split_large_chunks': False})
# ==========================================================

def main():
    ZARR_PATH = "TY-Dip_2.1.1.zarr"
    script_dir = Path(__file__).resolve().parent
    zarr_path = script_dir / ZARR_PATH
    
    if not zarr_path.exists():
        print(f"ERROR: {zarr_path} does not exist")
        return 1
    
    # Load all available pyramid levels
    multiscale_data = []
    for level in ['0', '1', '2', '3', '4']:
        p = zarr_path / level
        if p.exists():
            multiscale_data.append(da.from_zarr(str(p)))

    viewer = napari.Viewer(title="CRUK Stitched Volume - 128GB Optimized")
    
    layers = []
    n_channels = multiscale_data[0].shape[0]
    
    for c in range(n_channels):
        channel_layers = [level[c] for level in multiscale_data]
        
        # Calculate contrast using level 2 (fast)
        calc_level = min(len(channel_layers) - 1, 2)
        sample = channel_layers[calc_level][channel_layers[calc_level].shape[0]//2].compute()
        p1, p99 = np.percentile(sample, [1, 99.9])

        layer = viewer.add_image(
            channel_layers,
            name=f"Channel_{c}",
            multiscale=True,
            colormap='green' if c == 0 else 'magenta',
            contrast_limits=[float(p1), float(p99)],
            blending='additive',
            rendering='mip',  # Start with Maximum Intensity Projection
            cache=True
        )
        layers.append(layer)

    # ==================== INTERACTIVE Z-SCALING ====================
    @magicgui(auto_call=True, z_scale={'widget_type': 'FloatSlider', 'min': 0.1, 'max': 10.0, 'step': 0.1})
    def scale_widget(z_scale: float = 1.0):
        for layer in layers:
            # Update only the Z-component of the scale (index 1 in C,Z,Y,X)
            new_scale = list(layer.scale)
            new_scale[1] = z_scale
            layer.scale = new_scale

    viewer.window.add_dock_widget(scale_widget, area='right', name="3D Geometry")
    # ==============================================================

    print("\nPRO TIP: Run with 'export NAPARI_ASYNC=1' for smoothest rotation.")
    napari.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
