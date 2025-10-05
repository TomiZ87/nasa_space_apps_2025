import earthaccess  # needed to discover and download TEMPO data
import netCDF4 as nc  # needed to read TEMPO data
import numpy as np

def read_TEMPO_NO2_L3(fn):
    with nc.Dataset(fn) as ds:  # open read access to file
        # Open the 'product' group.
        prod = ds.groups["product"]

        # Read variable vertical_column_stratosphere from the product group.
        var = prod.variables["vertical_column_stratosphere"]
        strat_NO2_column = var[:]  # retrieve the numpy array.
        fv_strat_NO2 = var.getncattr("_FillValue")

        # Read variable 'vertical_column_troposphere' from the product group.
        var = prod.variables["vertical_column_troposphere"]
        trop_NO2_column = var[:]
        fv_trop_NO2 = var.getncattr("_FillValue")
        NO2_unit = var.getncattr("units")

        # Read variable 'main_data_quality_flag' from the product group.
        QF = prod.variables["main_data_quality_flag"][:]

        # Read latitude and longitude variables, from the root (/) group, into a numpy array.
        lat = ds.variables["latitude"][:]
        lon = ds.variables["longitude"][:]

    return lat, lon, strat_NO2_column, fv_strat_NO2, trop_NO2_column, fv_trop_NO2, NO2_unit, QF


def main():
    # Authenticate Earth Access
    auth = earthaccess.login(persist=True)

    short_name = "TEMPO_NO2_L3"  # collection name to search for in the EarthData
    version = "V03"

    # Point of interest: NASA Langley Research Center, HamptonVA, USA
    # latitude 37.1036 deg, longitude -76.3868 deg
    POI_lat = 37.1036
    POI_lon = -76.3868
    date_start = "2024-09-01 00:00:00"
    date_end = "2024-09-01 23:59:59"

    POI_results = earthaccess.search_data(
        short_name=short_name,
        version=version,
        temporal=(date_start, date_end),
        point=(POI_lon, POI_lat),  # search by point of interest
    )

    print("POI results:", len(POI_results))

    dlat = 5.0  # deg
    dlon = 6.0  # deg

    bbox_results = earthaccess.search_data(
        short_name=short_name,
        version=version,
        temporal=(date_start, date_end),
        bounding_box=(
            POI_lon - dlon,
            POI_lat - dlat,
            POI_lon + dlon,
            POI_lat + dlat,
        ),  # search by bounding box
    )

    print("BBOX results:", len(bbox_results))

    print("POI_results[8]:", POI_results[8])

    for r in POI_results:
        granule_name = r.data_links()[0].split("/")[-1]
        print(granule_name)

    files = earthaccess.download(POI_results[8:10], local_path=".")

    granule_name = POI_results[8].data_links()[0].split("/")[-1]
    print(granule_name)

    lat, lon, strat_NO2_column, fv_strat_NO2, trop_NO2_column, fv_trop_NO2, NO2_unit, QF = (
        read_TEMPO_NO2_L3(granule_name)
    )

    # Define a region of interest.
    dlat = 5  # deg
    dlon = 6  # deg
    mask_lat = (lat > POI_lat - dlat) & (lat < POI_lat + dlat)
    mask_lon = (lon > POI_lon - dlon) & (lon < POI_lon + dlon)

    # Subset NO2 column arrays.
    trop_NO2_column_loc = trop_NO2_column[0, mask_lat, :][:, mask_lon]
    print("trop_NO2_column_loc", trop_NO2_column_loc)
    strat_NO2_column_loc = strat_NO2_column[0, mask_lat, :][:, mask_lon]
    print("strat_NO2_column_loc", strat_NO2_column_loc)

    # Create 2D arrays of latitudes and longitudes, by repeating lon/lat along rows/columns.
    nlat, nlon = trop_NO2_column_loc.shape
    lon_loc_2D = np.vstack([lon[mask_lon]] * nlat)
    print("lon_loc_2D", lon_loc_2D)
    lat_loc_2D = np.column_stack([lat[mask_lat]] * nlon)
    print("lat_loc_2D", lat_loc_2D)

if __name__ == "__main__":
    main()
