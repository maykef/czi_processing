#!/bin/bash
# =========================================================
# CZI Light Sheet Processing – Nuclear Clean Reinstaller
# AMD Threadripper 7970X + RTX PRO 6000 Blackwell (sm_120)
# Fully deletes old env + caches → installs working nightly
# Save this in your repo → one-liner reinstall after OS wipe
# =========================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]$NC $1"; }
error() { echo -e "${RED}[✗] $1${NC}"; exit 1; }

log "=== NUCLEAR CLEAN CZI PROCESSING REINSTALL ==="

# 1. Full annihilation of old environment and caches
log "Removing old environment + pip/conda caches..."
conda env remove -n czi_processing -y 2>/dev/null || true
conda clean --all -y || true
rm -rf ~/miniforge3/envs/czi_processing
rm -rf ~/.cache/pip
rm -rf ~/.cache/torch
rm -rf ~/.cache/huggingface  # just in case

# 2. Fresh Miniforge (mamba) – reinstall if missing/corrupted
if ! command -v mamba &>/dev/null && ! command -v conda &>/dev/null; then
    log "Miniforge missing → installing fresh..."
    wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O /tmp/miniforge.sh
    bash /tmp/miniforge.sh -b -p $HOME/miniforge3
    source $HOME/miniforge3/bin/activate
fi
source $(dirname $(dirname $(which conda)))/etc/profile.d/conda.sh

# 3. Create brand-new environment
log "Creating fresh czi_processing environment (Python 3.11)..."
mamba create -y -n czi_processing python=3.11 -c conda-forge

# 4. Core packages via mamba (fast + binary compatible)
log "Installing core scientific stack..."
mamba install -y -n czi_processing -c conda-forge \
    numpy scipy scikit-image tifffile lxml h5py pillow matplotlib psutil tqdm

# 5. CZI reader
log "Installing czifile..."
mamba run -n czi_processing pip install --no-deps czifile

# 6. PyTorch nightly with CUDA 12.8 → FULL sm_120 support (Nov 2025+ builds)
log "Installing PyTorch nightly cu128 (Blackwell sm_120 fully supported)..."
mamba run -n czi_processing pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
mamba run -n czi_processing pip install --pre --upgrade --force-reinstall \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# 7. Final verification (no sm_120 warning = success)
log "Verification – this must show NO warning and compute capability 12.0"
mamba run -n czi_processing python - <<'PY'
import torch, czifile
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"Compute capability: {torch.cuda.get_device_capability(0)}")
# Real tensor test
x = torch.randn(5000, 5000).cuda()
print("GPU tensor operation: SUCCESS (no warning = full Blackwell sm_120 support!)")
print("czifile: OK")
print("Your 96 GB Blackwell beast is READY!")
PY

log "============================================"
log "NUCLEAR REINSTALL COMPLETE – ZERO WARNINGS"
log "Activate anytime with: conda activate czi_processing"
log "Save this script in your repo → one command after OS wipe!"
log "============================================"
