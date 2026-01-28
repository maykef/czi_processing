#!/usr/bin/env python3
"""
CZI Dataset Information Extractor
=================================
Extracts all key metadata needed for stitching pipeline decisions

Usage:
    python czi_info.py <path_to_czi_file>
    python czi_info.py *.czi  # Check all CZI files
"""

import sys
from pathlib import Path
from aicspylibczi import CziFile
import xml.etree.ElementTree as ET

def format_bytes(bytes_val):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def extract_czi_info(czi_path):
    """Extract comprehensive CZI metadata"""
    
    print(f"\n{'='*80}")
    print(f"CZI DATASET: {czi_path.name}")
    print(f"{'='*80}")
    
    try:
        czi = CziFile(str(czi_path))
        
        # === BASIC DIMENSIONS ===
        print(f"\n📊 DIMENSIONS")
        print(f"{'-'*80}")
        
        dims = czi.get_dims_shape()[0]
        dims_str = czi.dims
        is_mosaic = czi.is_mosaic()
        
        print(f"  Dimension string: {dims_str}")
        print(f"  Is mosaic: {is_mosaic}")
        print(f"  Full size: {czi.size}")
        
        print(f"\n  Key dimensions:")
        n_z = dims.get('Z', (0, 1))[1]
        n_c = dims.get('C', (0, 1))[1]
        n_m = dims.get('M', (0, 0))[1]
        tile_y = dims.get('Y', (0, 0))[1]
        tile_x = dims.get('X', (0, 0))[1]
        
        print(f"    Z-slices: {n_z}")
        print(f"    Channels: {n_c}")
        print(f"    Mosaic tiles (M): {n_m}")
        print(f"    Tile size: {tile_y} × {tile_x} pixels")
        
        # === STITCHING REQUIREMENTS ===
        print(f"\n🔧 STITCHING PARAMETERS")
        print(f"{'-'*80}")
        
        total_planes = n_z * n_c
        print(f"  Total planes to stitch: {total_planes} ({n_z} Z × {n_c} C)")
        
        if is_mosaic and n_m > 0:
            # Estimate stitched size
            try:
                bbox = czi.get_all_mosaic_scene_bounding_boxes()
                if bbox:
                    first_bbox = list(bbox.values())[0]
                    stitched_y = first_bbox.h
                    stitched_x = first_bbox.w
                    print(f"  Stitched plane size: {stitched_y} × {stitched_x} pixels")
                    
                    # Memory estimate
                    bytes_per_plane = stitched_y * stitched_x * 2  # uint16
                    mem_per_plane = bytes_per_plane / 1024**2
                    print(f"  Memory per plane: ~{mem_per_plane:.0f} MB")
                    print(f"  Peak memory (blending): ~{mem_per_plane * 1.5:.0f} MB")
                else:
                    print(f"  Stitched size: Unable to determine")
            except:
                print(f"  Stitched size: Unable to determine")
        else:
            print(f"  No stitching needed (not a mosaic)")
        
        # === STORAGE ESTIMATES ===
        print(f"\n💾 STORAGE ESTIMATES")
        print(f"{'-'*80}")
        
        if is_mosaic and n_m > 0:
            try:
                # Estimate based on single plane
                test_plane = czi.read_mosaic(Z=0, C=0, scale_factor=1.0)
                while test_plane.ndim > 2 and test_plane.shape[0] == 1:
                    test_plane = test_plane[0]
                
                plane_y, plane_x = test_plane.shape
                bytes_per_plane = plane_y * plane_x * 2
                
                # TIFF output (with compression ~0.6 ratio)
                tiff_size = total_planes * bytes_per_plane * 0.6
                # ZARR output (with compression ~0.45 ratio)
                zarr_size = total_planes * bytes_per_plane * 0.45
                
                print(f"  Stitched TIFFs: ~{format_bytes(tiff_size)}")
                print(f"  ZARR volume: ~{format_bytes(zarr_size)}")
                print(f"  Total required: ~{format_bytes(tiff_size + zarr_size)}")
            except Exception as e:
                print(f"  Unable to estimate: {e}")
        
        # === PROCESSING TIME ===
        print(f"\n⏱️  ESTIMATED PROCESSING TIME")
        print(f"{'-'*80}")
        
        if is_mosaic:
            # Based on benchmark: ~6 planes/sec with 28 workers
            rate_planes_per_sec = 6.0
            stitch_time_min = total_planes / rate_planes_per_sec / 60
            zarr_time_min = 15  # Typical for large dataset
            
            print(f"  Stitching ({total_planes} planes @ 6 pl/s): ~{stitch_time_min:.1f} minutes")
            print(f"  ZARR conversion: ~{zarr_time_min} minutes")
            print(f"  Total pipeline: ~{stitch_time_min + zarr_time_min:.1f} minutes")
        else:
            print(f"  No stitching required")
        
        # === METADATA FROM XML ===
        print(f"\n📋 ACQUISITION METADATA")
        print(f"{'-'*80}")
        
        meta = czi.meta
        
        # Extract key metadata
        metadata = {}
        
        # Scan for useful tags
        for elem in meta.iter():
            tag = elem.tag.split('}')[-1]  # Remove namespace
            
            if tag == 'CreationDate':
                metadata['Acquisition Date'] = elem.text
            elif tag == 'UserName':
                metadata['User'] = elem.text
            elif tag == 'IlluminationType':
                metadata['Illumination'] = elem.text
            elif tag == 'ContrastMethod':
                metadata['Contrast Method'] = elem.text
            elif tag == 'AcquisitionMode':
                metadata['Mode'] = elem.text
            elif tag == 'Medium':
                metadata['Immersion Medium'] = elem.text
            elif tag == 'RefractiveIndex':
                metadata['Refractive Index'] = elem.text
            elif tag == 'ObjectiveName' and elem.text:
                metadata['Objective'] = elem.text
            elif tag == 'IlluminationWavelength':
                for child in elem:
                    if child.tag.endswith('SinglePeak'):
                        channel = metadata.get('Illumination Wavelengths', [])
                        channel.append(f"{child.text} nm")
                        metadata['Illumination Wavelengths'] = channel
        
        # Print collected metadata
        for key, value in metadata.items():
            if isinstance(value, list):
                print(f"  {key}: {', '.join(value)}")
            else:
                print(f"  {key}: {value}")
        
        # === RECOMMENDATIONS ===
        print(f"\n💡 RECOMMENDATIONS")
        print(f"{'-'*80}")
        
        if is_mosaic and n_m > 0:
            print(f"  ✓ Use: stitch_v3_parallel.py")
            print(f"  ✓ Workers: 28 (adjust based on RAM)")
            print(f"  ✓ Then: convert_to_zarr.py for napari viewing")
            
            # Check if large dataset
            if total_planes > 1000:
                print(f"  ⚠️  Large dataset - ensure sufficient disk space")
                print(f"  ⚠️  Recommended: Process on NVMe for speed")
        else:
            print(f"  ℹ️  Not a mosaic - direct viewing possible")
        
        print(f"\n{'='*80}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExample:")
        print("  python czi_info.py sample.czi")
        print("  python czi_info.py *.czi")
        sys.exit(1)
    
    # Process all provided files
    czi_files = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_file() and path.suffix.lower() == '.czi':
            czi_files.append(path)
        elif '*' in arg:
            # Glob pattern
            czi_files.extend(Path('.').glob(arg))
    
    if not czi_files:
        print("ERROR: No CZI files found")
        sys.exit(1)
    
    print(f"\nFound {len(czi_files)} CZI file(s)")
    
    success_count = 0
    for czi_path in czi_files:
        if extract_czi_info(czi_path):
            success_count += 1
    
    print(f"Processed {success_count}/{len(czi_files)} files successfully")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
