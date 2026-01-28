Run dependencies.sh to install mamba env and libraries.

Run czi_info.py. for example python czi_info.py TY_Dip_2.1.1_Z1_Veh_488_638_Whole.czi

Run stitch_to_tif.py, the name of the file is hardcoded inside the script. 

Transform the tif files to a zarr pyramid using tif_to_zarr.py

View images with napari_zarr.py: NAPARI_ASYNC=1 python napari_zarr.py
