# UAS Trajectory processing using RTKLIB for Agisoft Metashape
 
 A workflow for processing ppk trajectories using rtklib. Designed around the DJI phantom 4 pro and Agisoft Metashape.

## Workflow

### Step 1: data organization and setup

1. Download the latest version of rtklib. I am using the demo5 fork - http://rtkexplorer.com/downloads/rtklib-code/
1. Create a copy of the PROJECT_TEMPLATE directory and insert the following files:
    - 01_BASE - Base rinex observation and navigation file/s
    - 02_ROVER - Create a new directory for each flight containing the rover rinex observation file/s and the image timestamp file (.MRK).
    - 03_EPHEMERIS - precise ephemeris (.sp3) and clock (.clk) data, download from - https://cddis.nasa.gov/archive/gnss/products/
    - 04_GEOID - The geoid grid file (.bin) with geoid heights for the survey location, in North America, download from - https://www.ngs.noaa.gov/GEOID/
    - 05_ANTENNAS - Antenna Calibration file (.atx) containing the antenna offset for the base and/or rover.
    - 06_OUT - directory to contain output files
1. If you haven't already, derive the position of the base station into geodetic coordinates using OPUS or similar.


### Step 2: Running the RTKPOST GUI

1. Run the RTKPOST GUI.
1. Select the rover, base, navigation, and ephemeris (optional) data to use, and select the 06_OUT directory as the output directory.
1. Select the options button and then under the setting1 tab enter the following:
    - Positioning mode: Kinematic
    - Frequencies: L1/L2
    - Filter type: Combined
    - Elevation Mask: 15 (should be default)
    - Rec Dynamics: on (should be default)
    - Satellite ephemeris: Precise (only if using precise ephemeris, else set to broadcast)
    - Constellations: GPS, GLONASS, GALILEO (dependent on antenna used)
1. Move to the setting2 tab and enter the following:
    - Integer Ambiguity: Fix and hold
1. Move to the output tab and select the following:
    - Solution Format: Lat/Lon/Height
    - Output Header: Off
    - Output Processing Options: Off
    - Time Format: ww ssss GPST
    - Latitude Longitude format: ddd.dddddd
    - Field Separator: comma (,)
1. Move to the files tab
    - Select the Antenna calibrations file in the second Satellite/Receiver box (for the base), and in the first box (for the rover).
1. Save the options for future use.
1. Move to the positions tab
    - Enter the coordinates to use for the base reference station.
    - Enter the antenna height offset height.
    - Select the Antenna Type.
1. Select ok to close the options, then click the execute button to start the trajectory processing.
1. Click the plot button, and make sure all/most of the ambiguities are fixed (Q=1).
1. This should have generated a *.pos file in the output folder containing the processed trajectory coordinates. This will be used in the next step.

### Step 3: Extracting the camera exterior orientation rotation parameters.

The exif data in the images contains valuable rotation parameter data (roll, pitch, yaw). The easiest way to get this information is using Agisoft Metashape as described below:

1. Load the images into Agisoft Metashape.
1. Under the "reference" pane click export
    - enter a filename ({flightName}_inclination.txt)
    - Under items select "cameras"
    - Under delimiter select "comma"
    - Under columns select "save rotation"
    - Click ok
1. This should have generated a file containing the rotation (Yaw, Roll, Pitch) parameters for each image.

### Step 4: Interpolating the camera exterior orientation translation parameters in a projected coordinate system.

Next we need to interpolate the position of the camera at each image within a projected coordinate system. This can be done using the trajectory.py code in this repo as described below:  
1. Install the dependencies from this repo if not already (pip install -r requirements.txt)
1. Run the trajectory.py script and select the following files:
    - Select the rtklib *.pos file(s) generated in step 2.
    - Select the rotation *.txt file(s) from agisoft metashape generated in step 3.
    - Select the timestamp *.MRK file(s) that contains the timestamp of each image.
    - *(optional)* Select the geoid *.bin file covering the survey area. For the US, these are available from NGS: https://www.ngs.noaa.gov/GEOID/
1. Enter the EPSG code of the projected coordinate system you would like to use, if unknown, these can be found at https://epsg.io/
1. Enter a multiplier to scale the standard deviation values reported by rtklib.
    - The standard deviation values can be used as uncertainty estimates in agisoft metashape to constrain the camera origins. The standard deviation values outputted by rtklib (and other GNSS post processing software) are often overly optimistic of the actual uncertainty and thus scaling these values by a constant factor can provide a more reasonable uncertainty estimate. In my experience, 10 is a good default multiplier.

1. This should generate an output text file ({filename}_cameras.txt) containing the exterior camera orientation parameters (rotation and translation) for each image in a local projection where Z represents the orthometric height.

### Step 5: Next Steps

The outputted text file can be imported into Agisoft Metashape by clicking the import button under the "reference" pane or any other data processing software. As always control points/data should be used to verify any products resulting from the processed trajectory. This guide is a simplified workflow primarily designed around the DJI phantom 4 pro and Agisoft Metashape, it is the responsibility of the user to make sure this is suitable for their own workflow. 