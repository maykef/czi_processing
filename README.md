# CZI Processing Pipeline

A high-performance Python-based pipeline for processing large Zeiss `.czi` mosaic datasets (200GB+).  
This toolkit stitches mosaic tiles into full-resolution planes, converts them into multiscale **OME-Zarr**, and visualizes them in **Napari** with correct physical scaling.

Optimized for the **AMD Threadripper 7970X** and **Samsung 9100 Pro** hardware configuration.

---

## Features

- **Hardware Overdrive**  
  Parallel stitching using 48+ workers to saturate 32-core / 64-thread CPUs.

- **NVMe Optimized**  
  Large-chunk Zarr writing designed to hit the sequential write limits of PCIe 5.0 drives.

- **Automated Workflow**  
  End-to-end processing from raw CZI to multiscale Zarr with a single command.

- **Correct 3D Scaling**  
  Automatic Z-axis stretching in Napari based on microscope metadata (Z ÷ XY ratio).

- **Memory Efficient**  
  Stable processing for 200GB+ datasets within 128GB RAM limits using Dask and optimized accumulators.

---

## Repository Structure

```text
.
├── master_pipeline.py   # CLI wrapper for the full end-to-end process
├── stitch_to_tif.py     # Parallel mosaic stitching (argparse)
├── tif_to_zarr.py       # TIFF stack → multiscale OME-Zarr (argparse)
├── napari_zarr.py       # Standalone viewer with 3D scale correction
└── dependencies.sh      # Environment setup
```

---

## Installation

### Create the environment

This repository requires **Python 3.11** and is optimized for Linux-based workstation environments.

```bash
bash dependencies.sh
conda activate czi_processing
```

---

## Usage

### Full Pipeline

```bash
python master_pipeline.py --czi your_data.czi --out your_data.zarr --view
```

**Arguments**

- `--czi` — Input Zeiss `.czi` filename  
- `--out` — Desired OME-Zarr output name  
- `--view` — Automatically launch Napari  
- `--temp` — Optional scratch directory for intermediate TIFFs

---

### Manual Stitching

```bash
python stitch_to_tif.py your_data.czi output_folder/
```

---

### Manual Zarr Conversion

```bash
python tif_to_zarr.py input_folder/ output_data.zarr
```

---

### Interactive 3D Viewing

```bash
python napari_zarr.py your_data.zarr
```

**3D Scaling Note**  
A Z-stretch (~3.08×) is applied using 0.65 µm XY and 2.0 µm Z-step metadata.

---

## Performance Benchmarks

| Dataset Size | Stitching | Zarr Conversion | Total |
|-------------:|----------:|----------------:|------:|
| 62 GB        | 1.0 min   | 2.7 min         | 3.7 min |
| 211 GB       | 3.7 min   | 11.5 min        | 15.4 min |

---

## Output Formats

### TIFF (Intermediate)

- One file per `(C, Z)` plane  
- `uint16`, zlib level 1 compression

### OME-Zarr (Final)

- Multiscale pyramid (levels 0–4)  
- Axes: `C, Z, Y, X`  
- Chunk size: `(1, 64, 512, 512)`

---

## License

Add your preferred license here.
