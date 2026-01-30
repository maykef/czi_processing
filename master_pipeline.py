#!/usr/bin/env python3
import argparse
import subprocess
import time
from pathlib import Path

def run_step(command, description):
    print(f"\n>>> {description}...")
    start = time.time()
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"Error in {description}")
        exit(1)
    return time.time() - start

def main():
    parser = argparse.ArgumentParser(description="TR-7970X Extreme Pipeline")
    parser.add_argument("--czi", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--view", action="store_true", help="Launch Napari automatically")
    args = parser.parse_args()

    temp_dir = "temp_tiff_buffer"
    total_start = time.time()

    # Step 1: Stitching (High CPU Usage)
    run_step(["python", "stitch_to_tif.py", args.czi, temp_dir], "Stitching")

    # Step 2: Zarr (High NVMe Usage) 
    run_step(["python", "tif_to_zarr.py", temp_dir, args.out], "Converting to OME-Zarr")

    print(f"\nPipeline Finished in {(time.time() - total_start)/60:.2f} minutes")

    if args.view:
        # Calls the standalone script we wrote above
        subprocess.run(["python", "napari_zarr.py", args.out])

if __name__ == "__main__":
    main()
