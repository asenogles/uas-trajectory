import os
import pandas as pd
import numpy as np
from pyproj import CRS
from pyproj import Transformer
from tkinter import Tk
from tkinter.filedialog import askopenfilename


def open_file(filetype, title):
    root = Tk()
    root.withdraw()
    filename = askopenfilename(filetypes=filetype, title=title)
    return filename


def stats(df):
    fix_percent = df["Q"].value_counts(sort=True, normalize=True)
    if 1 in fix_percent.index:
        print(
            "{:.2f}% of measurements had fixed ambiguities\n".format(fix_percent[1] * 100)
        )
    else:
        print("0% of measurements had fixed ambiguities\n")

    print(
        "Average standard deviation estimates of position components are:\n"
        "Northing: {:.3f}\n"
        "Easting: {:.3f}\n"
        "Height: {:.3f}\n".format(df["sdn"].mean(), df["sde"].mean(), df["sdu"].mean())
    )
    print("average number of satellites used was: {:.2f}\n".format(df["ns"].mean()))


def geodeticToProj(lat, lon, ellip, proj_out, proj_in=6319):
    """Convert geodetic coordinates to projected coordinate system

    Parameters:
        lat (np.array): latitudes
        lon (np.array): longitudes
        ellip (np.height): ellipsoid heights
        proj_out (int): epsg code of output projected coordinate system
        proj_in (int): epsg code of input geodetic coordinate system, defaults to NAD83 (2011)

    Returns:
        tuple: X, Y, Z of projected coordinate system
    """

    # Define transformation parameters
    geodetic = CRS.from_epsg(proj_in)
    projected = CRS.from_epsg(proj_out)
    transformer = Transformer.from_crs(geodetic, projected)

    # Transform coordinates
    return transformer.transform(lat, lon, ellip)


def applyGeoid(lat, lon, ellip, model):
    """Converts ellipsoid height to orthometric height

    Parameters:
        lat (np array): latitudes
        lon (np array): longitudes
        ellip (np array): ellipsoid heights
        model (str): path to geoid model file to use

    Returns:
        (np array) orthometric heights"""
    import pygeodesy as pg

    geoid = pg.GeoidG2012B(model)
    return ellip - geoid.height(lat, lon)


def interpolatePosition(pos, mrk):
    """interpolates the camera coordinates using GPS time

    Parameters:
        pos (pandas.dataframe): dataframe containing the trajectory
        mrk (pandas.dataframe): dataframe containing timestamps of images

    Returns:
        (pd.dataframe): dataframe of interpoloated camera coordinates
    """

    mrk["X"] = np.interp(mrk["GPST"], pos["GPST"], pos["X"])
    mrk["Y"] = np.interp(mrk["GPST"], pos["GPST"], pos["Y"])
    mrk["Z"] = np.interp(mrk["GPST"], pos["GPST"], pos["Z"])
    mrk["sde"] = np.interp(mrk["GPST"], pos["GPST"], pos["sde"])
    mrk["sdn"] = np.interp(mrk["GPST"], pos["GPST"], pos["sdn"])
    mrk["sdu"] = np.interp(mrk["GPST"], pos["GPST"], pos["sdu"])

    return mrk


def leverArm(df):
    """Applies the lever arm correction to each image.

    This uses the lever arm corrections provided in a ENU frame, and thus does NOT account for
    differences between the ENU Frame and the projected coordinate system (deflection of the vertical).
    These differences are for the most part miniscule.

    Parameters:
        df (pandas.dataframe): dataframe containing the camera position and leverarm corrections

    Returns:
        (pd.dataframe): dataframe of corrected camera positions
    """

    df["X"] = df["X"] + df["leverE"] / 1000
    df["Y"] = df["Y"] + df["leverN"] / 1000
    df["Z"] = df["Z"] - df["leverD"] / 1000
    return df


if __name__ == "__main__":

    print("Select the rtklib '.pos' file\n")
    rtklib_file = open_file(
        (("pos files", "*.pos"), ("All files", "*.*")), "rtklib pos file"
    )
    print("Select the orientation '.txt' file containing rotation values\n")
    orient_file = open_file(
        (("txt files", "*.txt"), ("All files", "*.*")), "Rotation file"
    )
    print("Select the image timestamp '.MRK' file\n")
    time_file = open_file(
        (("MRK files", "*.MRK"), ("All files", "*.*")), "timestamp file"
    )
    print("Select the geoid '.bin' file\n")
    ortho_model = open_file(
        (("geoid files", "*.bin"), ("All files", "*.*")), "geoid file"
    )

    # Setup output file and directory
    os.chdir(os.path.dirname(rtklib_file))
    output_file = os.path.basename(rtklib_file)
    output_file, _ = os.path.splitext(output_file)
    output_file = output_file + "_cameras" + ".txt"

    # Read the files into panda dataframes
    pos = pd.read_csv(
        rtklib_file,
        sep=",",
        skiprows=1,
        names=[
            "week",
            "GPST",
            "lat",
            "lon",
            "height",
            "Q",
            "ns",
            "sdn",
            "sde",
            "sdu",
            "sdne",
            "sdeu",
            "sdun",
            "age",
            "ratio",
        ],
        header=0,
        index_col=False,
    )
    orient = pd.read_csv(
        orient_file,
        sep=",",
        skiprows=1,
        usecols=["#Label", "Yaw", "Roll", "Pitch"],
        header=0,
        index_col=False,
    )
    time = pd.read_csv(
        time_file,
        sep="\t",
        usecols=[0, 1, 3, 4, 5],
        names=["photoID", "GPST", "leverN", "leverE", "leverD"],
        index_col=False,
    )

    # Remove additional characters from lever arm columns
    time["leverN"] = time["leverN"].map(lambda x: x.rstrip(",N")).astype("int32")
    time["leverE"] = time["leverE"].map(lambda x: x.rstrip(",E")).astype("int32")
    time["leverD"] = time["leverD"].map(lambda x: x.rstrip(",V")).astype("int32")

    # print stats of rtklib pos file
    stats(pos)

    # Get the output coordinate system
    print(
        "Example EPSG codes:\n",
        "OCRS Oregon Coast NAD83(2011) meters: 6842\n",
        "OCRS Salem NAD83(2011) meters: 6858\n",
        "Oregon State Plane North NAD83(2011) meters: 6558\n",
        "Oregon State Plane South NAD83(2011) meters: 6560\n",
    )
    local_projection = int(
        input("Enter the EPSG code for the output coordinate system:\n")
    )
    # Scale accuracies
    acc_scale = float(
        input("Enter a multiplier to scale the standard devation values:\n")
    )

    # convert to numpy arrays
    lat = pos["lat"].to_numpy()
    lon = pos["lon"].to_numpy()
    ellip = pos["height"].to_numpy()

    # Reproject the data
    pos["X"], pos["Y"], ellip = geodeticToProj(lat, lon, ellip, local_projection)

    # Convert ellipsoid height to ortho height
    pos["Z"] = applyGeoid(lat, lon, ellip, ortho_model)

    # Remove excess from Pos dataframe
    pos = pos[["GPST", "X", "Y", "Z", "sde", "sdn", "sdu"]]

    # merge the image timestamp dataframe with the rotation dataframe
    if len(time) == len(orient):
        mrk = orient.join(time).drop(["photoID"], axis=1)
    else:
        raise ValueError("Orientation and timestamp file do not match")

    # Interpolate the position of the camera at the image timestamp
    interpol = interpolatePosition(pos, mrk)

    # Apply lever arm offset to camera coordinates
    camera_origin = leverArm(interpol)

    # Scale the accuracy values
    camera_origin["sde"] = camera_origin["sde"] * acc_scale
    camera_origin["sdn"] = camera_origin["sdn"] * acc_scale
    camera_origin["sdu"] = camera_origin["sdu"] * acc_scale

    # Clean up and export
    reorder = ["#Label", "X", "Y", "Z", "Yaw", "Pitch", "Roll", "sde", "sdn", "sdu"]
    camera_origin = camera_origin[reorder]
    camera_origin.to_csv(output_file, index=False, float_format="%.5f")

    input(
        "Success! Output file wrote to {}\n\nPress enter to continue".format(
            os.getcwd() + "\\" + output_file
        )
    )