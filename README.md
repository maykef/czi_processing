# CZI Processing Pipeline

A Python-based pipeline for **processing large Zeiss `.czi` mosaic datasets**, stitching tiles into full-resolution planes, converting them into **multiscale OME-Zarr**, and visualizing them interactively in **Napari**.

This repository is designed for **lightsheet and tiled microscopy data** where raw CZI files are too large or too slow to explore directly.

---

## Features

- Inspect CZI metadata and estimate resource requirements  
- Stitch mosaic tiles into full-resolution 2D planes  
- Blend overlapping tiles with linear edge falloff  
- Export stitched planes as compressed TIFFs  
- Convert TIFF stacks into **multiscale OME-Zarr**  
- Fast 3D visualization in **Napari** with multiscale support  
- Dask-based lazy loading and chunked computation  

---

## Repository Structure

```
.
├── dependencies.sh      # Conda environment setup
├── czi_info.py          # Inspect CZI metadata and estimate output size
├── stitch_to_tif.py     # Parallel mosaic stitching → TIFF planes
├── tif_to_zarr.py       # TIFF stack → multiscale OME-Zarr
├── napari_zarr.py       # Napari viewer for the generated Zarr
└── README.md
```

---

## Installation

### 1. Create the environment

This repo uses **Conda / Mamba** and Python **3.11**.

```bash
bash dependencies.sh
conda activate czi_processing
```

Installed dependencies include:
- aicspylibczi
- numpy, scipy, scikit-image
- tifffile
- dask, distributed, zarr
- napari, pyqt

Optional: CUDA-enabled PyTorch (prompted during install).

---

## Typical Workflow

```
CZI file
  ↓
Metadata inspection
  ↓
Mosaic stitching → TIFF planes
  ↓
TIFF stack → multiscale OME-Zarr
  ↓
Interactive 3D viewing in Napari
```

---

## Step-by-Step Usage

### 1. Inspect a CZI file

```bash
python czi_info.py your_dataset.czi
```

Prints dataset dimensions, mosaic layout, estimated output sizes, time estimates, and selected acquisition metadata.

---

### 2. Stitch mosaic tiles to TIFF

Edit configuration variables at the top of `stitch_to_tif.py`:

```python
CZI_FILENAME = "your_dataset.czi"
OUTPUT_DIR = "stitched_tifs"
N_WORKERS = 16
BLEND_PIXELS = 80
```

Run:

```bash
python stitch_to_tif.py
```

Output TIFF naming:
```
C{channel}_Z{z:04d}.tif
```

---

### 3. Convert TIFFs to multiscale OME-Zarr

Edit configuration in `tif_to_zarr.py`:

```python
INPUT_DIR = "stitched_tifs"
OUTPUT_ZARR = "dataset.zarr"
LEVELS = 4
CHUNK_SHAPE = (1, 32, 256, 256)
VOXEL_SIZE = [2.0, 0.65, 0.65]  # (Z, Y, X) microns
```

Run:

```bash
python tif_to_zarr.py
```

---

### 4. Visualize in Napari

Edit the Zarr path in `napari_zarr.py`:

```python
ZARR_PATH = "dataset.zarr"
```

Launch:

```bash
NAPARI_ASYNC=1 python napari_zarr.py
```

Features include multiscale loading, automatic contrast limits, voxel scaling, and a control dock for Z stretch and rotation.

---

## Output Formats

### TIFF
- One file per `(C, Z)` plane
- uint16, zlib-compressed

### OME-Zarr
- Multiscale pyramid (`0`, `1`, `2`, ...)
- Axes: `C, Z, Y, X`
- Compatible with Napari, MoBIE, Neuroglancer

---

## Assumptions & Limitations

- Some paths and settings are hardcoded
- Simple linear blending (no seam optimization)
- Assumes uint16 microscopy intensity data
- Single-scene CZI files

---

## Recommended Use Cases

- Lightsheet microscopy
- Large tiled acquisitions
- Whole-organ or whole-embryo datasets

---

## License

Add your preferred license here.
