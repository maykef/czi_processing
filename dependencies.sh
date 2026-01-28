#!/bin/bash
# =========================================================
# CZI Light Sheet Stitching Pipeline - Complete Environment
# AMD Threadripper 7970X + 128GB RAM + NVMe
# Installs everything needed for:
#   - CZI mosaic stitching with blending
#   - Parallel processing (multiprocessing)
#   - ZARR conversion for efficient viewing
#   - Napari visualization
# =========================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]$NC $1"; }
error() { echo -e "${RED}[✗] $1${NC}"; exit 1; }

log "=== CZI STITCHING PIPELINE INSTALLER ==="

# 1. Clean old environment
log "Removing old environment..."
conda env remove -n czi_processing -y 2>/dev/null || true
conda clean --all -y || true
rm -rf ~/miniforge3/envs/czi_processing
rm -rf ~/.cache/pip

# 2. Check Miniforge
if ! command -v mamba &>/dev/null && ! command -v conda &>/dev/null; then
    log "Installing Miniforge..."
    wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O /tmp/miniforge.sh
    bash /tmp/miniforge.sh -b -p $HOME/miniforge3
    source $HOME/miniforge3/bin/activate
fi
source $(dirname $(dirname $(which conda)))/etc/profile.d/conda.sh

# 3. Create environment
log "Creating czi_processing environment (Python 3.11)..."
mamba create -y -n czi_processing python=3.11 -c conda-forge

# 4. Core scientific packages
log "Installing scientific stack..."
mamba install -y -n czi_processing -c conda-forge \
    numpy scipy scikit-image tifffile psutil

# 5. CZI reading library
log "Installing aicspylibczi (for Zeiss CZI mosaic files)..."
mamba run -n czi_processing pip install aicspylibczi

# 6. ZARR and Dask for efficient storage/lazy loading
log "Installing zarr + dask for efficient volume storage..."
mamba install -y -n czi_processing -c conda-forge \
    zarr dask distributed

# 7. Napari for 3D visualization
log "Installing napari for visualization..."
mamba install -y -n czi_processing -c conda-forge napari pyqt

# 8. Optional: PyTorch for GPU-accelerated processing (if needed later)
read -p "Install PyTorch nightly with CUDA 12.8? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Installing PyTorch nightly cu128..."
    mamba run -n czi_processing pip install --pre \
        torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
fi

# 9. Verification
log "Verifying installation..."
mamba run -n czi_processing python - <<'PY'
import sys
print("\n=== Package Verification ===")

try:
    import numpy as np
    print(f"✓ NumPy {np.__version__}")
except:
    print("✗ NumPy FAILED")

try:
    from aicspylibczi import CziFile
    print(f"✓ aicspylibczi (CZI reading)")
except:
    print("✗ aicspylibczi FAILED")

try:
    import zarr
    print(f"✓ zarr {zarr.__version__}")
except:
    print("✗ zarr FAILED")

try:
    import dask.array as da
    print(f"✓ dask (lazy loading)")
except:
    print("✗ dask FAILED")

try:
    import napari
    print(f"✓ napari {napari.__version__}")
except:
    print("✗ napari FAILED")

try:
    from tifffile import imwrite
    print(f"✓ tifffile (TIFF I/O)")
except:
    print("✗ tifffile FAILED")

try:
    from scipy.ndimage import distance_transform_edt
    print(f"✓ scipy (blending functions)")
except:
    print("✗ scipy FAILED")

try:
    from multiprocessing import Pool
    print(f"✓ multiprocessing (parallel stitching)")
except:
    print("✗ multiprocessing FAILED")

print("\n=== System Info ===")
import psutil
print(f"CPU cores: {psutil.cpu_count()}")
print(f"RAM: {psutil.virtual_memory().total / 1024**3:.1f} GB")

print("\n✓ ENVIRONMENT READY FOR CZI STITCHING")
PY

log "============================================"
log "INSTALLATION COMPLETE"
log "Activate: conda activate czi_processing"
log ""
log "Pipeline scripts:"
log "  1. stitch_v3_parallel.py  - Parallel tile stitching"
log "  2. convert_to_zarr.py     - Convert to efficient format"
log "  3. view_zarr.py           - View in napari"
log "============================================"
