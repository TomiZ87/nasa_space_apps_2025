import codecs  # needed to read Pandora data
import os
import platform
import requests  # needed to search for and download Pandora data
import shutil
import sys
from datetime import datetime  # needed to work with time in plotting time series
from pathlib import Path  # needed to check whether a needed data file is already downloaded
from subprocess import Popen
from urllib.request import urlopen  # needed to search for and download Pandora data

import earthaccess  # needed to discover and download TEMPO data
import matplotlib.pyplot as plt  # needed to plot the resulting time series
import netCDF4 as nc  # needed to read TEMPO data
import numpy as np

from scipy.interpolate import griddata  # needed to interpolate TEMPO data to the point of interest
from scipy import stats  # needed for linear regression analysis
from shapely.geometry import Point, Polygon  # needed to search a point within a polygon

# function read_pandora_web returns the list of available Pandora sites
def read_pandora_web():
    url = "https://data.pandonia-global-network.org/"
    page = urlopen(url)
    html_bytes = page.read()
    html = html_bytes.decode("utf-8")

    big_line = str(html)
    lines = big_line.split("\n")

    ref_lines = [i for i in lines if "href" in i]
    refs = []
    for line in ref_lines:
        pos1 = line.find('"')
        pos2 = line.rfind('"')
        if pos1 > 0 and pos2 > pos1 and line[pos2 - 1] == "/" and line[pos1 + 1] == ".":
            refs.append(line[pos1 + 3 : pos2 - 1])

    return refs


# function check_site checks whether user entered site is in the list of available Pandora sites
def check_site(site_name, refs):
    site_list = []
    for line in refs:
        if site_name in line:
            site_list.append(line)

    return site_list


# function take_pandora_sites takes user input and checks whether the site is in the list of available Pandora sites
def take_pandora_sites(refs):
    print("please select a Pandora site name from the list")
    for ref in refs:
        print(ref)

    answer = "y"
    while answer == "y":
        site_name = input("Enter a name of a Pandora site: ")
        print(site_name)
        site_list = check_site(site_name, refs)
        site_num = len(site_list)
        if site_num == 0:
            print("site ", site_name, "was not found")
            continue

        if site_num > 1:
            print("there are ", site_num, " site names, select one from")
            for site in site_list:
                print(site)

            site_name = input("Enter a name of a Pandora site: ")
            if site_list.count(site_name) != 1:
                print("Entered name is not the exact match of one of the following sites")
                for site in site_list:
                    print(site)
                print("program terminated")
                sys.exit()

            for site in site_list:
                if site == site_name:
                    pandora_site = site_name
                    print("site ", site_name, "was found and added to the list of sites ")
                    break

        if site_num == 1:
            pandora_site = site_list[0]
            print("site ", site_list[0], "was found and added to the list of sites ")

        answer = "n"

    return pandora_site


# Pandora site may have several instruments. In this case each instrument has its own directory.
# However, the most recent version of the NO2 data, rnvs3p1-8, is available only in one of these directories.
# The function creates all possible links, but some of them may be non-existing. This is checked and cleared later.
def instrument_path(site):
    # function instrument_path returns links to possible Pandora NO2 retrievals files
    url = "https://data.pandonia-global-network.org/" + site + "/"
    page = urlopen(url)
    html_bytes = page.read()
    html = html_bytes.decode("utf-8")

    big_line = str(html)
    lines = big_line.split("\n")

    ref_lines = [i for i in lines if "href" in i]
    links = []
    for line in ref_lines:
        pos1 = line.find('"')
        pos2 = line.rfind('"')
        if 0 < pos1 < pos2 and line[pos2 - 1] == "/" and line[pos1 + 3 : pos1 + 10] == "Pandora":
            link = (
                url
                + line[pos1 + 3 : pos2]
                + "L2/"
                + line[pos1 + 3 : pos2 - 1]
                + "_"
                + site
                + "_L2_rnvs3p1-8.txt"
            )
            print(link)
            links.append(link)

    return links


# function downloading Pandora data file with given url
def download(url):
    response = requests.get(url)
    response_code = response.status_code

    file_name = url.split("/")[-1]

    if response_code == 200:
        content = response.content
        data_path = Path(file_name)
        data_path.write_bytes(content)

    return file_name, response_code



# function converting Pandora timestamp into a set of  year, month, day, hour, minute, and second
# function read_timestamp converts Pandora timestamp of the format
# 'yyyymmddThhmmssZ' into a set of 6 numbers:
# integer year, month, day, hour, minute, and real second.
def read_timestamp(timestamp):
    yyyy = int(timestamp[0:4])
    mm = int(timestamp[4:6])
    dd = int(timestamp[6:8])
    hh = int(timestamp[9:11])
    mn = int(timestamp[11:13])
    ss = float(timestamp[13:17])

    return yyyy, mm, dd, hh, mn, ss


# function reading Pandora NO2 data file rnvs3p1-8
#
# Below is the second version of function read_Pandora_NO2_rnvs3p1_8. It is to be used for the future validation efforts.
# The difference with the original version is that instead of discriminating negative values of the total NO2 column,
# it uses quality flags. It was previously found that QF == 0 does not occure often enough,
# so we will have to use QF == 10 (not-assured high quality).
#
# function read_Pandora_NO2_rnvs3p1-8 reads Pandora total NO2 column data files ending with rnvs3p1-8.
# Arguments:
# fname - name file to be read, string;
# start_date - beginning of the time interval of interest,
#              integer of the form YYYYMMDD;
# end_date -   end of the time interval of interest,
#              integer of the form YYYYMMDD.
#
# if start_date is greater than end_date, the function returns a numpy array
# with shape (0, 8), otherwise it returns an 8-column numpy array
# with with columns being year, month, day, hour, minute, second of observation
# and retrieved total NO2 column along with its total uncertainty.
#
# NO2 column is in mol/m^2, so conversion to molecules/cm^2 is performed by
# multiplication by Avogadro constant, NA =  6.02214076E+23, and division by 1.E+4
def read_Pandora_NO2_rnvs3p1_8_v2(fname, start_date, end_date):
    conversion_coeff = 6.02214076e19  # Avogadro constant divided by 10000

    data = np.empty([0, 8])
    if start_date > end_date:
        return -999.0, -999.0, data

    with codecs.open(fname, "r", encoding="utf-8", errors="ignore") as f:
        while True:
            # Get next line from file
            line = f.readline()

            if line.find("Short location name:") >= 0:
                loc_name = line.split()[-1]  # location name, to be used in the output file name
                print("location name ", loc_name)

            if line.find("Location latitude [deg]:") >= 0:
                lat = float(line.split()[-1])  # location latitude
                print("location latitude ", lat)

            if line.find("Location longitude [deg]:") >= 0:
                lon = float(line.split()[-1])  # location longitude
                print("location longitude ", lon)

            if line.find("--------") >= 0:
                break

        while True:
            # Get next line from file
            line = f.readline()

            if line.find("--------") >= 0:
                break

        while True:
            # now reading line with data
            line = f.readline()

            if not line:
                break

            line_split = line.split()

            yyyy, mm, dd, hh, mn, ss = read_timestamp(line_split[0])
            date_stamp = yyyy * 10000 + mm * 100 + dd
            if date_stamp < start_date or date_stamp > end_date:
                continue

            QF = int(line_split[35])  # quality flag

            if QF == 0 or QF == 10:
                column = float(line_split[38])
                column_unc = float(line_split[42])  # total column uncertainty
                data = np.append(
                    data,
                    [
                        [
                            yyyy,
                            mm,
                            dd,
                            hh,
                            mn,
                            ss,
                            column * conversion_coeff,
                            column_unc * conversion_coeff,
                        ]
                    ],
                    axis=0,
                )

    return lat, lon, loc_name, data


def read_TEMPO_NO2_L2(fn):
    """
    function read_TEMPO_NO2_L2 reads the following arrays from the
    TEMPO L2 NO2 product TEMPO_NO2_L2_V03:
      'main_data_quality_flag';
      'vertical_column_stratosphere';
      'vertical_column_troposphere';
      'vertical_column_troposphere_uncertainty'.
    It returns these variable along with their fill values and coordinates of the pixels.

    Some pixels may have only one of stratospheric OR tropospheric columns valid with the other being filled.
    In these pixels the function returns fill value in total column and its uncertainty.

    This function DO NOT WORK with V01 and V02 data files as their format is different.
    If a user need to READ total column from array 'vertical_column_total', he need to change this function.
    Currently, in version V03 arrays 'vertical_column_total' and 'vertical_column_total_uncertrainty' are located in 'support_data' group.

    If one requested variables cannot be read, all returned variables are zeroed
    """

    var_name = "vertical_column_stratosphere"

    try:
        with nc.Dataset(fn) as ds:
            prod = ds.groups["product"]  # this opens group product, /product, as prod

            # this reads variable vertical_column_stratosphere from prod (group product, /product)
            var = prod.variables[var_name]
            strat_NO2_column = np.array(var)
            fv_strat_NO2 = var.getncattr("_FillValue")

            # this reads variable 'vertical_column_troposphere' from prod (group product, /product)
            var = prod.variables["vertical_column_troposphere"]
            trop_NO2_column = np.array(var)
            fv_trop_NO2 = var.getncattr("_FillValue")
            prod_unit = var.getncattr("units")

            # this reads 'vertical_column_troposphere_uncertainty' from prod (group product, /product)
            var = prod.variables["vertical_column_troposphere_uncertainty"]
            trop_NO2_column_unc = np.array(var)
            fv_trop_NO2_column_unc = var.getncattr("_FillValue")

            # this reads variable 'main_data_quality_flag' from prod (group product, /product)
            var = prod.variables["main_data_quality_flag"]
            QF = np.array(var)
            fv_QF = var.getncattr("_FillValue")

            geo = ds.groups["geolocation"]  # this opens group geolocation, /geolocation, as geo

            # this reads geolocation variables from geo (geolocation group, /geolocation) into a numpy array
            lat = np.array(geo.variables["latitude"])
            lon = np.array(geo.variables["longitude"])
            fv_geo = geo.variables["latitude"].getncattr("_FillValue")
            time = np.array(geo.variables["time"])

    except Exception as error:
        print(error)
        #print("variable " + var_name + " cannot be read in file " + fn)
        lat = 0.0
        lon = 0.0
        time = 0.0
        fv_geo = 0.0
        trop_NO2_column = 0.0
        strat_NO2_column = 0.0
        trop_NO2_column_unc = 0.0
        QF = 0.0
        fv_trop_NO2 = 0.0
        fv_strat_NO2 = 0.0
        fv_trop_NO2_column_unc = 0.0
        fv_QF = -999
        prod_unit = ""

    print(lat,
        lon,
        fv_geo,
        time,
        strat_NO2_column,
        fv_strat_NO2,
        trop_NO2_column,
        fv_trop_NO2,
        trop_NO2_column_unc,
        fv_trop_NO2_column_unc,
        prod_unit,
        QF,
        fv_QF,)

    return (
        lat,
        lon,
        fv_geo,
        time,
        strat_NO2_column,
        fv_strat_NO2,
        trop_NO2_column,
        fv_trop_NO2,
        trop_NO2_column_unc,
        fv_trop_NO2_column_unc,
        prod_unit,
        QF,
        fv_QF,
    )


def main():
    auth = earthaccess.login(strategy="interactive", persist=True)
    homeDir = os.path.expanduser("~") + os.sep

    with open(homeDir + ".dodsrc", "w") as file:
        file.write("HTTP.COOKIEJAR={}.urs_cookies\n".format(homeDir))
        file.write("HTTP.NETRC={}.netrc".format(homeDir))
        file.close()

    print("Saved .dodsrc to:", homeDir)

    # Set appropriate permissions for Linux/macOS
    if platform.system() != "Windows":
        Popen("chmod og-rw ~/.netrc", shell=True)
    else:
        # Copy dodsrc to working directory in Windows
        shutil.copy2(homeDir + ".dodsrc", os.getcwd())
        print("Copied .dodsrc to:", os.getcwd())

    # Discovering existing Pandora stations and selecting one of them
    # Discovering available Pandora site.
    # Please bear in mind that some sites do not have NO2 data files
    print("gathering Pandora sites information")
    refs = read_pandora_web()

    pandora_site = take_pandora_sites(refs)  # create list of Pandora sites of interest
    print("the following sites were selected")
    print(pandora_site)
    print("from the list of existing Pandora sites")

    # create a list of !AVAILABLE! Pandora files for the Pandora site
    pandora_files = []

    links = instrument_path(pandora_site)

    npfiles = 0

    for link in links:
        pandora_fname = link.split("/")[-1]

        # check if file exists in the local directory, if not download from Pandora site
        if not os.path.exists(pandora_fname):
            print(pandora_fname, " does not exit in local directory, downloading from the web")
            print(link)

            pandora_fname, response_code = download(link)

            if response_code == 200:
                print("Pandora L2 file ", pandora_fname, " has been downloaded")
                npfiles = npfiles + 1
                pandora_files.append(pandora_fname)
            else:
                print("Pandora L2 file ", link, " does not exist")

        else:
            print(pandora_fname, " exits in local directory")
            npfiles = npfiles + 1
            pandora_files.append(pandora_fname)

    if npfiles == 0:  # no files were found, STOP here
        print("no files were found for Pandora site ", pandora_site, "program terminated")
        sys.exit()
    if npfiles > 1:  # normally there should be only one file per site. if there are more - STOP
        #  print('there are too many files for site ', pandora_site, '- STOP and investigate file names below. Program terminated')
        print("there are more than 1 files for site ", pandora_site)
        #  for pandora_fname in pandora_files: print(pandora_fname)
        for i, link in enumerate(links):
            print(i, link)
        num = int(input("please enter the number for the link"))
        pandora_fname, response_code = download(links[num])
    #  sys.exit()

    print("enter period of interest, start and end dates, in the form YYYYMMDD")
    datestamp_ini = input("enter start date of interest ")
    datestamp_fin = input("enter end date of interest ")

    start_date = int(datestamp_ini)
    end_date = int(datestamp_fin)

    yyyy_ini = start_date // 10000
    mm_ini = start_date // 100 - yyyy_ini * 100
    dd_ini = start_date - yyyy_ini * 10000 - mm_ini * 100

    yyyy_fin = end_date // 10000
    mm_fin = end_date // 100 - yyyy_fin * 100
    dd_fin = end_date - yyyy_fin * 10000 - mm_fin * 100
    print(yyyy_ini, mm_ini, dd_ini, yyyy_fin, mm_fin, dd_fin)

    date_start = str("%4.4i-%2.2i-%2.2i 00:00:00" % (yyyy_ini, mm_ini, dd_ini))
    date_end = str("%4.4i-%2.2i-%2.2i 23:59:59" % (yyyy_fin, mm_fin, dd_fin))

    pandora_file = pandora_files[0]
    lat, lon, POI_name, Pandora_data = read_Pandora_NO2_rnvs3p1_8_v2(pandora_file, start_date, end_date)

    if lat == -999.0:
        print("error reading pandora file ", pandora_file, "program terminated")
        sys.exit()

    POI = np.array([lat, lon])

    # print # of points in Pandora timeseries
    n_Pandora_data = len(Pandora_data)
    print(
        n_Pandora_data,
        " Pandora measurements found within period of interes between",
        date_start,
        "and",
        date_end,
    )
    if n_Pandora_data == 0:
        print("program terminated")
        sys.exit()

    short_name = "TEMPO_NO2_L2"  # collection name to search for in the EarthData
    out_Q = "NO2_tot_col"  # name of the output quantity with unit
    out_Q_unit = "molecules/cm^2"  # name of the output quantity with unit

    POI_name_ = POI_name.replace(" ", "_")
    Pandora_out = open(
        out_Q
        + "_Pandora_"
        + datestamp_ini
        + "_"
        + datestamp_fin
        + "_"
        + POI_name_
        + "_"
        + str("%08.4fN_%08.4fW.txt" % (POI[0], -POI[1])),
        "w",
    )
    for line in Pandora_data:
        Pandora_out.write(
            str(
                "%4.4i %2.2i %2.2i %2.2i %2.2i %4.1f %12.4e %12.4e\n"
                % (line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7])
            )
        )
    Pandora_out.close()

    auth = earthaccess.login()
    # auth.refresh_tokens()

    POI_lat = POI[0]
    POI_lon = POI[1]

    version = "V03"
    POI_results = earthaccess.search_data(
        short_name=short_name,
        version=version,
        temporal=(date_start, date_end),
        point=(POI_lon, POI_lat),
    )

    n_gr = len(POI_results)
    if n_gr == 0:
        print("program terminated")
        sys.exit()


    downloaded_files = earthaccess.download(POI_results, local_path=".")


    # Important note
    # NO2 total column is calculated is a sum of stratospheric and tropospheric columns.
    # One of them or both may be negative even with the highest quality flag.
    # The code below compiles TWO timeseries one takes all values of total NO2 column,
    # while another discards negative values before interpolation to the POI is performed.
    # The two timeseries will be plotted later to see the difference, if any.
    # This feature may be commented out should the user be not interested in accounting positive-only retrievals.

    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    fout_noFV = open(
        out_Q
        + "_noFV_"
        + datestamp_ini
        + "_"
        + datestamp_fin
        + "_"
        + POI_name_
        + "_"
        + str("%08.4fN_%08.4fW.txt" % (POI[0], -POI[1])),
        "w",
    )
    fout_noFV.write(
        "timeseries of "
        + out_Q
        + " at "
        + POI_name
        + " "
        + str("%08.4fN %08.4fW" % (POI[0], -POI[1]))
        + "\n"
    )
    fout_noFV.write("yyyy mm dd hh mn ss " + out_Q_unit + "\n")

    fout_noneg = open(
        out_Q
        + "_noneg_"
        + datestamp_ini
        + "_"
        + datestamp_fin
        + "_"
        + POI_name_
        + "_"
        + str("%08.4fN_%08.4fW.txt" % (POI[0], -POI[1])),
        "w",
    )
    fout_noneg.write(
        "timeseries of "
        + out_Q
        + " at "
        + POI_name
        + " "
        + str("%08.4fN %08.4fW" % (POI[0], -POI[1]))
        + "\n"
    )
    fout_noneg.write("yyyy mm dd hh mn ss " + out_Q_unit + "\n")

    for file in downloaded_files:
        (
            lat,
            lon,
            fv_geo,
            time,
            strat_NO2_column,
            fv_strat_NO2,
            trop_NO2_column,
            fv_trop_NO2,
            trop_NO2_column_unc,
            fv_trop_NO2_column_unc,
            prod_unit,
            QF,
            fv_QF,
        ) = read_TEMPO_NO2_L2(file)

        print("lat and lon: ", lat, lon)
        print("time: ", time)
        print("strat_NO2_column: ", strat_NO2_column)
        print("trop_NO2_column: ", trop_NO2_column)
        print("trop_NO2_column_unc: ", trop_NO2_column_unc)


        if isinstance(lat, float):
            continue

            #  polygon = TEMPO_L2_polygon(lat, lon, fv_geo)

            #  coords_poly = list(polygon)
            #  poly = Polygon(coords_poly)

        nx = lon.shape[0]
        ny = lon.shape[1]

        # getting time from the granule filename
        Tind = file.rfind("T")
        yyyy = int(file[Tind - 8: Tind - 4])
        mm = int(file[Tind - 4: Tind - 2])
        dd = int(file[Tind - 2: Tind])
        hh = int(file[Tind + 1: Tind + 3])
        mn = int(file[Tind + 3: Tind + 5])
        ss = float(file[Tind + 5: Tind + 7])

        pp = np.array([POI[1], POI[0]])
        p = Point(pp)  # POI[0] - latitudes, POI[1] - longitudes

        POI_found = False
        for ix in range(nx - 1):
            for iy in range(ny - 1):
                if lon[ix, iy] == fv_geo:
                    continue
                if lat[ix, iy] == fv_geo:
                    continue
                if lon[ix, iy + 1] == fv_geo:
                    continue
                if lat[ix, iy + 1] == fv_geo:
                    continue
                if lon[ix + 1, iy + 1] == fv_geo:
                    continue
                if lat[ix + 1, iy + 1] == fv_geo:
                    continue
                if lon[ix + 1, iy] == fv_geo:
                    continue
                if lat[ix + 1, iy] == fv_geo:
                    continue

                coords_poly_loc = [
                    [lon[ix, iy], lat[ix, iy]],
                    [lon[ix, iy + 1], lat[ix, iy + 1]],
                    [lon[ix + 1, iy + 1], lat[ix + 1, iy + 1]],
                    [lon[ix + 1, iy], lat[ix + 1, iy]],
                ]
                poly_loc = Polygon(coords_poly_loc)

                if p.within(poly_loc):
                    POI_found = True
                    strat_NO2_column_loc = strat_NO2_column[ix: ix + 2, iy: iy + 2]
                    trop_NO2_column_loc = trop_NO2_column[ix: ix + 2, iy: iy + 2]
                    total_NO2_column_unc_loc = trop_NO2_column_unc[ix: ix + 2, iy: iy + 2]
                    total_NO2_column_loc = np.full((2, 2), fv_trop_NO2)
                    mask_valid = (
                            (strat_NO2_column_loc != fv_strat_NO2)
                            & (trop_NO2_column_loc != fv_trop_NO2)
                            & (total_NO2_column_unc_loc != fv_trop_NO2_column_unc)
                    )
                    total_NO2_column_loc[mask_valid] = (
                            strat_NO2_column_loc[mask_valid] + trop_NO2_column_loc[mask_valid]
                    )
                    QF_loc = QF[ix: ix + 2, iy: iy + 2]
                    lat_loc = lat[ix: ix + 2, iy: iy + 2]
                    lon_loc = lon[ix: ix + 2, iy: iy + 2]

                    print("scanl pixel latitude  longitude  NO2_tot_col NO2_tot_col_unc NO2_col_QF")
                    for scl in range(2):
                        for pix in range(2):
                            print(
                                "  %3d  %4d %9.6f %10.6f %11.4e   %11.4e %5i"
                                % (
                                    ix + scl,
                                    iy + pix,
                                    lat_loc[scl, pix],
                                    lon_loc[scl, pix],
                                    total_NO2_column_loc[scl, pix],
                                    total_NO2_column_unc_loc[scl, pix],
                                    QF_loc[scl, pix],
                                )
                            )

                    print("POI", POI_name, "at", POI[1], POI[0], " found")

                    mask_noFV = mask_valid & (QF_loc == 0)
                    mask_noneg = (
                            (strat_NO2_column_loc > 0)
                            & (trop_NO2_column_loc > 0)
                            & (total_NO2_column_unc_loc != fv_trop_NO2_column_unc)
                            & (QF_loc == 0)
                    )
                    points_noFV = np.column_stack((lon_loc[mask_noFV], lat_loc[mask_noFV]))
                    points_noneg = np.column_stack((lon_loc[mask_noneg], lat_loc[mask_noneg]))
                    ff_noFV = strat_NO2_column_loc[mask_noFV] + trop_NO2_column_loc[mask_noFV]
                    ff_noneg = strat_NO2_column_loc[mask_noneg] + trop_NO2_column_loc[mask_noneg]
                    ff_unc_noFV = total_NO2_column_unc_loc[mask_noFV]
                    ff_unc_noneg = total_NO2_column_unc_loc[mask_noneg]
                    print(ff_unc_noFV)
                    print(ff_unc_noneg)

                    # handling time first:
                    delta_t = (time[ix + 1] + time[ix]) * 0.5 - time[0]
                    ss = ss + delta_t
                    if ss >= 60.0:
                        delta_mn = int(ss / 60.0)
                        ss = ss - 60.0 * delta_mn
                        mn = mn + delta_mn
                        if mn >= 60:
                            mn = mn - 60
                            hh = hh + 1
                            if hh == 24:
                                hh = hh - 24
                                dd = dd + 1
                                day_month = days[mm]
                                if (yyyy // 4) * 4 == yyyy and mm == 2:
                                    day_month = day_month + 1
                                if dd > day_month:
                                    dd = 1
                                    mm = mm + 1
                                    if mm > 12:
                                        mm = 1
                                        yyyy = yyyy + 1

                    if ff_noFV.shape[0] == 0:
                        continue
                    elif ff_noFV.shape[0] < 4:
                        total_NO2_column_noFV = np.mean(ff_noFV)
                        total_NO2_column_unc_noFV = np.mean(ff_unc_noFV)
                    elif ff_noFV.shape[0] == 4:
                        total_NO2_column_noFV = griddata(
                            points_noFV, ff_noFV, pp, method="linear", fill_value=-1.0, rescale=False
                        )[0]
                        total_NO2_column_unc_noFV = griddata(
                            points_noFV,
                            ff_unc_noFV,
                            pp,
                            method="linear",
                            fill_value=-1.0,
                            rescale=False,
                        )[0]

                    fout_noFV.write(
                        str(
                            "%4.4i %2.2i %2.2i %2.2i %2.2i %4.1f %10.3e %10.3e "
                            % (
                                yyyy,
                                mm,
                                dd,
                                hh,
                                mn,
                                ss,
                                total_NO2_column_noFV,
                                total_NO2_column_unc_noFV,
                            )
                        )
                    )
                    for scl in range(2):
                        for pix in range(2):
                            fout_noFV.write(
                                str(
                                    "%9.4fN %9.4fW %10.3e %10.3e "
                                    % (
                                        lat_loc[scl, pix],
                                        -lon_loc[scl, pix],
                                        trop_NO2_column_loc[scl, pix],
                                        total_NO2_column_unc_loc[scl, pix],
                                    )
                                )
                            )
                    fout_noFV.write("\n")

                    if ff_noneg.shape[0] == 0:
                        continue
                    elif ff_noneg.shape[0] < 4:
                        total_NO2_column_noneg = np.mean(ff_noneg)
                        total_NO2_column_unc_noneg = np.mean(ff_unc_noneg)
                    elif ff_noneg.shape[0] == 4:
                        total_NO2_column_noneg = griddata(
                            points_noneg, ff_noneg, pp, method="linear", fill_value=-1.0, rescale=False
                        )[0]
                        total_NO2_column_unc_noneg = griddata(
                            points_noneg,
                            ff_unc_noneg,
                            pp,
                            method="linear",
                            fill_value=-1.0,
                            rescale=False,
                        )[0]

                    fout_noneg.write(
                        str(
                            "%4.4i %2.2i %2.2i %2.2i %2.2i %4.1f %10.3e %10.3e "
                            % (
                                yyyy,
                                mm,
                                dd,
                                hh,
                                mn,
                                ss,
                                total_NO2_column_noneg,
                                total_NO2_column_unc_noneg,
                            )
                        )
                    )
                    for scl in range(2):
                        for pix in range(2):
                            fout_noneg.write(
                                str(
                                    "%9.4fN %9.4fW %10.3e %10.3e "
                                    % (
                                        lat_loc[scl, pix],
                                        -lon_loc[scl, pix],
                                        trop_NO2_column_loc[scl, pix],
                                        total_NO2_column_unc_loc[scl, pix],
                                    )
                                )
                            )
                    fout_noneg.write("\n")

                    break

            if POI_found:
                break


    fout_noFV.close()
    fout_noneg.close()

if __name__ == "__main__":
    main()
