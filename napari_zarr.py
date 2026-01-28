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
from qtpy.QtCore import QTimer

# ==================== MICROSCOPE SETTINGS ====================
XY_PIXEL_SIZE = 0.65  # microns
Z_STEP_SIZE = 2.0     # microns
AUTO_Z_STRETCH = Z_STEP_SIZE / XY_PIXEL_SIZE
# =============================================================

cache = Cache(40e9) 
cache.register()
dask.config.set({'array.slicing.split_large_chunks': False})

def main():
    ZARR_PATH = "TY-Dip_2.1.1.zarr"
    script_dir = Path(__file__).resolve().parent
    zarr_path = script_dir / ZARR_PATH
    
    if not zarr_path.exists():
        print(f"ERROR: {zarr_path} does not exist")
        return 1
    
    multiscale_data = []
    for level in ['0', '1', '2', '3', '4']:
        p = zarr_path / level
        if p.exists():
            multiscale_data.append(da.from_zarr(str(p)))

    viewer = napari.Viewer(title=f"CRUK Volume - Fixed Scale: {AUTO_Z_STRETCH:.2f}")
    layers = []
    
    # FIXED: Scale must be (Z, Y, X) for the image layer
    # Napari ignores the 'C' dimension when setting layer scale
    base_scale = [AUTO_Z_STRETCH, 1.0, 1.0] 
    
    for c in range(multiscale_data[0].shape[0]):
        # Extract channel c from all scales
        channel_layers = [level[c] for level in multiscale_data]
        
        calc_level = min(len(channel_layers) - 1, 2)
        sample = channel_layers[calc_level][channel_layers[calc_level].shape[0]//2].compute()
        p1, p99 = np.percentile(sample, [1, 99.9])

        layer = viewer.add_image(
            channel_layers,
            name=f"Channel_{c}",
            multiscale=True,
            scale=base_scale,  # Now correctly 3D
            colormap='green' if c == 0 else 'magenta',
            contrast_limits=[float(p1), float(p99)],
            blending='additive',
            rendering='mip',
            cache=True
        )
        layers.append(layer)

    # ==================== REFINED CONTROLS ====================
    timer = QTimer()
    def rotate_camera():
        current_angles = list(viewer.camera.angles)
        current_angles[1] += 1.0 
        viewer.camera.angles = tuple(current_angles)
    timer.timeout.connect(rotate_camera)

    @magicgui(
        call_button="Toggle Rotation",
        manual_z_stretch={'label': 'Fine Tune Z', 'widget_type': 'FloatSlider', 'min': 0.1, 'max': 10.0, 'value': AUTO_Z_STRETCH},
        speed={'label': 'Speed', 'widget_type': 'Slider', 'min': 1, 'max': 50, 'value': 10}
    )
    def tools_widget(manual_z_stretch: float = AUTO_Z_STRETCH, speed: int = 10):
        for layer in layers:
            new_scale = list(layer.scale)
            # In 3D layer scale, Z is index 0 (Scale is Z, Y, X)
            new_scale[0] = manual_z_stretch
            layer.scale = new_scale
        
        if timer.isActive():
            timer.stop()
        else:
            timer.start(100 // speed)

    viewer.window.add_dock_widget(tools_widget, area='right', name="3D Controls")

    print(f"Applied Auto Z-Stretch: {AUTO_Z_STRETCH:.2f}")
    napari.run()

if __name__ == "__main__":
    sys.exit(main())
