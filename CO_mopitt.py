import os
from pathlib import Path

import cartopy.crs as ccrs
import earthaccess
import h5py
import numpy as np

def main():
    earthaccess.login()
    short_name = "MOP03JM"
    version = "9"

    results = earthaccess.search_data(
        short_name=short_name,
        version=version,
        provider="LARC_CLOUD",  # this is needed only temporary, while there are still non-LARC_CLOUD versions of these granules.
        temporal=("2024-09", "2024-10"),
    )

    downloaded_files = earthaccess.download(results, local_path=".")

    arrays = {"lon": [], "lat": [], "CO_mixing_ratio": []}

    # Open and read file
    for i, file in enumerate(downloaded_files):
        with h5py.File(file, mode="r") as f:
        # Slice data to get the pressure level of your choice
        #   [Longitude(Xdim):360 , Latitude(Ydim):180, Presure level:9]
        #   Pressure Level: 0 = 900 hPa, 1 = 800 hPa, 2 = 700 hPa, 3 = 600 hPa
        #   4 = 500 hPa, 5 = 400 hpa, 6 = 300 hPa, 7 = 200 hPa, 8 = 100 hPa
            data = f["/HDFEOS/GRIDS/MOP03/Data Fields/RetrievedCOMixingRatioProfileDay"][:]
            data = np.transpose(data)

            # Retrieve the lat and lon data as well as the area of your choice
            lon = f["/HDFEOS/GRIDS/MOP03/Data Fields/Longitude"][:]
            lat = f["/HDFEOS/GRIDS/MOP03/Data Fields/Latitude"][:]

            # Turn the -9999.0 into a NaN
            masked_data = np.ma.masked_where(data <= 0, data)
            CO_mixing_ratio = data.copy()
            CO_mixing_ratio[masked_data <= 0] = np.nan

            arrays["lon"].append(lon)
            arrays["lat"].append(lat)
            arrays["CO_mixing_ratio"].append(CO_mixing_ratio)

    print(arrays)

    print(f"{len(results)} file(s) found.")


if __name__ == "__main__":
    main()
