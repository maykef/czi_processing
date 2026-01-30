CZI Processing Pipeline

A high-performance Python-based pipeline optimized for processing large Zeiss .czi mosaic datasets (200GB+). This toolkit handles stitching mosaic tiles into full-resolution planes, converting them into multiscale OME-Zarr, and visualizing them in Napari with correct physical scaling.

Optimized specifically for high-core-count workstations (e.g., AMD Threadripper 7970X) and PCIe 5.0 NVMe storage.
Features

    Hardware Overdrive: Parallel stitching using 48+ workers and optimized Zarr writing to saturate NVMe bandwidth.

    Automated Workflow: Execute the entire process from raw CZI to multiscale Zarr with a single command.

    Smart Blending: Shared weight caching for fast, linear edge falloff blending.

    Correct 3D Scaling: Automatic Z-axis stretching in Napari based on microscope metadata (Z÷XY ratio).

    Scalable: Successfully tested on datasets exceeding 200GB with stable memory management.

Repository Structure

.
├── master_pipeline.py   # NEW: CLI wrapper to run the full end-to-end process
├── stitch_to_tif.py     # Parallel mosaic stitching (Optimized for 48+ threads)
├── tif_to_zarr.py       # TIFF stack → multiscale OME-Zarr (NVMe optimized)
├── napari_zarr.py       # Standalone & integrated viewer with 3D scaling
└── dependencies.sh      # Environment setup

Installation
1. Create the environment

This repo uses Python 3.11 and is optimized for Linux-based workstation environments.
Bash

bash dependencies.sh
conda activate czi_processing

Usage
1. The Full Pipeline (Recommended)

Use master_pipeline.py to run stitching and Zarr conversion in sequence. This script automatically handles temporary file management.
Bash

python master_pipeline.py --czi your_data.czi --out your_data.zarr --view

Arguments:

    --czi: Input Zeiss filename.

    --out: Desired OME-Zarr output name.

    --view: (Optional) Automatically launch Napari when finished.

    --temp: (Optional) Define a custom scratch directory for intermediate TIFFs.

2. Manual Stitching

If you need to run the stitcher individually:
Bash

python stitch_to_tif.py your_data.czi output_folder/

Note: This version uses 48 workers by default to utilize high-end CPU threads.
3. Manual Zarr Conversion

To convert an existing folder of stitched TIFFs:
Bash

python tif_to_zarr.py input_folder/ output_data.zarr

Optimized for Samsung 9100 Pro or similar NVMe drives using larger chunk sizes (1, 64, 512, 512) to maximize sequential write speeds.
4. Interactive 3D Viewing

Launch the viewer on any processed Zarr:
Bash

python napari_zarr.py your_data.zarr

3D Scaling Support: The viewer is pre-configured for a Z-stretch of 3.08 (based on 0.65μm XY and 2.0μm Z-steps). This ensures your 3D volumes do not appear "flattened."
Hardware Benchmarks (Threadripper 7970X / Samsung 9100 Pro)
Dataset Size	Stitching Time	Zarr Conversion	Total Time
62 GB	1.0 min	2.7 min	~3.7 min
211 GB	3.7 min	11.5 min	~15.4 min
Configuration

For individual hardware tuning, the following parameters are found in the main() section of the respective scripts:

    N_WORKERS: Set to 48 for 32-core/64-thread CPUs.

    CHUNK_SIZE: Optimized at (1, 64, 512, 512) for NVMe scratch drives.

    Z_STRETCH: Adjust XY_PIXEL_SIZE and Z_STEP_SIZE in napari_zarr.py to match your microscope settings.
