I cannot provide a direct download link, but I can provide the complete, properly formatted Markdown code. You can copy this text, save it as a file named README.md in your project folder, and it will be ready for use.
CZI Processing Pipeline

A high-performance Python-based pipeline for processing large Zeiss .czi mosaic datasets (200GB+). This toolkit stitches mosaic tiles into full-resolution planes, converts them into multiscale OME-Zarr, and visualizes them in Napari with correct physical scaling.

Optimized for the AMD Threadripper 7970X and Samsung 9100 Pro hardware configuration.
Features

    Hardware Overdrive: Parallel stitching using 48+ workers to saturate 32-core/64-thread CPUs.

    NVMe Optimized: Large-chunk Zarr writing designed to hit the sequential write limits of PCIe 5.0 drives.

    Automated Workflow: End-to-end processing from raw CZI to multiscale Zarr with a single command.

    Correct 3D Scaling: Automatic Z-axis stretching in Napari based on microscope metadata (Z÷XY ratio).

    Memory Efficient: Stable processing for 200GB+ datasets within 128GB RAM limits using Dask and optimized accumulators.

Repository Structure
Plaintext

.
├── master_pipeline.py   # CLI wrapper for the full end-to-end process
├── stitch_to_tif.py     # Parallel mosaic stitching (Argparse version) 
├── tif_to_zarr.py       # TIFF stack → multiscale OME-Zarr (Argparse version)
├── napari_zarr.py       # Standalone viewer with 3D scale correction
└── dependencies.sh      # Environment setup 

Installation
1. Create the environment

This repo requires Python 3.11 and is optimized for Linux-based workstation environments.
Bash

bash dependencies.sh
conda activate czi_processing

Usage
1. The Full Pipeline

Use master_pipeline.py to run stitching and Zarr conversion in sequence. This handles temporary file management and optional visualization.
Bash

python master_pipeline.py --czi your_data.czi --out your_data.zarr --view

Arguments:

    --czi: Input Zeiss filename.

    --out: Desired OME-Zarr output name.

    --view: (Optional) Automatically launch Napari when finished.

    --temp: (Optional) Define a custom scratch directory for intermediate TIFFs.

2. Manual Stitching

To run the stitcher individually on a specific file:
Bash

python stitch_to_tif.py your_data.czi output_folder/

3. Manual Zarr Conversion

To convert a folder of previously stitched TIFFs into an OME-Zarr:
Bash

python tif_to_zarr.py input_folder/ output_data.zarr

4. Interactive 3D Viewing

Launch the viewer on any processed Zarr to inspect the results:
Bash

python napari_zarr.py your_data.zarr

3D Scaling Note: The viewer applies a Z-stretch (default: ~3.08) calculated from the 0.65μm XY and 2.0μm Z-step metadata to ensure the volume is not flattened in 3D mode.
Performance Benchmarks (TR 7970X / Samsung 9100 Pro)
Dataset Size	Stitching Time	Zarr Conversion	Total Pipeline Time
62 GB	1.0 min	2.7 min	~3.7 min
211 GB	3.7 min	11.5 min	~15.4 min
Output Formats
TIFF (Intermediate)

    One file per (C, Z) plane.

    uint16, zlib level 1 compressed (optimized for write speed over ratio).

OME-Zarr (Final)

    Multiscale pyramid (Levels 0 through 4).

    Axes: C, Z, Y, X.

    Chunk Size: (1, 64, 512, 512) for high-speed I/O.

License

Add your preferred license here.
