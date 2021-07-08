import struct
import numpy as np
from PIL import Image, ExifTags

""" 
    camera orientation data is in the MakerNotes field of DJI Phantom 4 images
    This field contains a binary array of different values

    See the following for more info:

    Fields in MakerNotes: https://exiftool.org/TagNames/DJI.html
    Fields in MakerNotes(2): https://github.com/drewnoakes/metadata-extractor-images/blob/master/jpg/metadata/dotnet/DJI%20Phantom%204%20(3).jpg.txt
    MakerNotes types: https://exiftool.org/makernote_types.html

    From what I can tell, each field is preceeded by 8 hexidecimal values representing  the field as follows:

    0-1: The tag ID of the field
    2-3: Representation of the data type (char, float int etc)
    4-7: Number of items in the field

    It likely contains 8 fields to ensure memory order - http://www.catb.org/esr/structure-packing/

    This header is followed by the field value, which is then followed by the next fields header etc

    From experimentation, I have found the fields in the following positions:

    MakerNotes_HEADER = MakerNote[0:2]
    MAKE_HEADER = MakerNote[2:10]
    make_value = MakerNote[10:14]
    UNKNOWN_HEADER = MakerNote[14:22]
    unknown_value = MakerNote[22:26]
    SPEED_X_HEADER = MakerNote[26:34]
    speed_x_value = MakerNote[34:38]
    SPEED_Y_HEADER = MakerNote[38:46]
    speed_y_value = MakerNote[46:50]
    SPEED_Z_HEADER = MakerNote[50:58]
    speed_z_value = MakerNote[58:62]
    PITCH_HEADER = MakerNote[62:70]
    pitch_value = MakerNote[70:74]
    YAW_HEADER = MakerNote[74:82]
    yaw_value = MakerNote[82:86]
    ROLL_HEADER = MakerNote[86:94]
    roll_value = MakerNote[94:98]
    CAMERA_PITCH_HEADER = MakerNote[98:106]
    camera_pitch_value = MakerNote[106:110]
    CAMERA_YAW_HEADER = MakerNote[110:118]
    camera_yaw_value = MakerNote[118:122]
    CAMERA_ROLL_HEADER = MakerNote[122:130]
    camera_roll_value = MakerNote[130:134]
"""

# Dict of Header tag ID's contained in DJI Phatom 4 MakerNotes field
HEADERS = {
    'MAKE': 0x0001,
    'UNKNOWN': 0x0002,
    'SPEED_X': 0x0003,
    'SPEED_Y': 0x0004,
    'SPEED_Z': 0x0005,
    'PITCH': 0x0006,
    'YAW': 0x0007,
    'ROLL': 0x0008,
    'CAMERA_PITCH': 0x0009,
    'CAMERA_YAW': 0x000a,
    'CAMERA_ROLL': 0x000b
}
key_list = list(HEADERS.keys())
val_list = list(HEADERS.values())

# Empty dict of fields contained in DJI Phatom 4 MakerNotes field
VALUES = {
    'MAKE': None,
    'UNKNOWN': None,
    'SPEED_X': None,
    'SPEED_Y': None,
    'SPEED_Z': None,
    'PITCH': None,
    'YAW': None,
    'ROLL': None,
    'CAMERA_PITCH': None,
    'CAMERA_YAW': None,
    'CAMERA_ROLL': None
}

def read_makerNotes(makerNotes, values=VALUES, i=0, starting_header=val_list[0]):
    """Read the maker notes into a python dict

    Args:
        makerNotes (byte str): byte string from the MakerNotes exif field
        values (dict, optional): python dict to place read files into
        i (int, optional): starting position in byte array. Defaults to 0.
        starting_header (hexadecimal, optional): starting header to identify. Defaults to 0x01.

    Raises:
        ValueError: if header tag id is unknown

    Returns:
        values (dict): values read from MakerNotes byte array
    """
    nextHeader = starting_header
    while True:
        if makerNotes[i] == nextHeader:
            pos = val_list.index(nextHeader)
            header = key_list[pos]
            print(f'found header {hex(int(makerNotes[i]))} ({header}) at position {i}')
            type = makerNotes[i+2] # read data type
            num = int(struct.unpack(b"<L", makerNotes[i+4:i+8])[0]) # read num of occurances
            dataType = b"<"
            if type == 0x01:     # pad
                dataType = dataType + (b"x" * num)
                size = num * 1
                data = struct.unpack(dataType, makerNotes[i+8:i+8+size])
            elif type == 0x02:  # char
                dataType = dataType + (b"c" * num)
                size = num * 1
                data = struct.unpack(dataType, makerNotes[i+8:i+8+size])
                data = ' '.join([d.decode() for d in data])[:-1]
            elif type == 0x0b:  # float
                dataType = dataType + (b"f" * num)
                size = num * 4
                data = struct.unpack(dataType, makerNotes[i+8:i+8+size])[num-1]
            else:
                raise ValueError(f'cannot identify type with hexadecimal representation: {type}')
            values[header] = data
            i = i + 8 + size - 1
            nextHeader += 1
            sumNones = sum([1 for key, val in values.items() if val is None])
            if sumNones == 0:
                break
        i+=1
    return values

def get_makerNotes(img, field_name='MakerNote'):
    """Gets the makerNotes field from the jpg exif data

    Args:
        img (PIL Image): Pillow image
        field_name (str, optional): name of field to extract. Defaults to 'MakerNote'.

    Returns:
        byte str: byte string contained in exif MakerNotes field
    """
    exif_data = img._getexif()
    keys = list(ExifTags.TAGS.keys())
    vals = list(ExifTags.TAGS.values())
    exif_index = vals.index(field_name)
    exif_num = keys[exif_index]
    MakerNote = exif_data[exif_num]
    return MakerNote

def euler2rot(R, P, Y):
    Rx = np.array([[ 1, 0, 0],
                   [ 0, np.cos(R),-np.sin(R)],
                   [ 0, np.sin(R), np.cos(R)]])

    Ry = np.array([[ np.cos(P), 0, np.sin(P)],
                   [ 0, 1, 0],
                   [-np.sin(P), 0, np.cos(P)]])

    Rz = np.array([[ np.cos(Y), -np.sin(Y), 0],
                   [ np.sin(Y), np.cos(Y) , 0],
                   [ 0, 0, 1]])
    return Rz.dot(Ry.dot(Rx))

def isRotationMatrix(rot) :
    rot_t = np.transpose(rot)
    shouldBeIdentity = np.dot(rot_t, rot)
    I = np.identity(3, dtype = rot.dtype)
    n = np.linalg.norm(I - shouldBeIdentity)
    return n < 1e-6

def rot2euler(rot) :
    assert(isRotationMatrix(rot))
    sy = np.sqrt(rot[0,0] * rot[0,0] +  rot[1,0] * rot[1,0])
    singular = sy < 1e-6
    if  not singular:
        r = np.arctan2(rot[2,1] , rot[2,2])
        p = np.arctan2(-rot[2,0], sy)
        y = np.arctan2(rot[1,0], rot[0,0])
    else:
        r = np.arctan2(-rot[1,2], rot[1,1])
        p = np.arctan2(-rot[2,0], sy)
        y = 0
    return np.array([r, p, y])

if __name__ == '__main__':
    from tkinter.filedialog import askopenfilename
    from tkinter import Tk
    root = Tk()
    root.withdraw()
    filename = askopenfilename(filetypes=(("jpg files", "*.jpg"), ("All files", "*.*")), title='select a jpg image')

    img = Image.open(filename)
    MakerNote = get_makerNotes(img) # Retrieves the MakerNotes binary string
    values = read_makerNotes(MakerNote) # reads the MakerNotes binary string into a python dict
    print('values read from MakerNotes field: ', values)

    # form roll, pitch yaw array
    craft_rpy = np.array([values['ROLL'], values['PITCH'], values['YAW'] % 360]) * np.pi / 180.0
    camera_rpy = np.array([values['CAMERA_ROLL'], values['CAMERA_PITCH'] + 90, values['CAMERA_YAW'] % 360]) * np.pi / 180.0

    # convert to rotation matrix
    craft_rot = euler2rot(craft_rpy[0], craft_rpy[1], craft_rpy[2])
    camera_rot = euler2rot(camera_rpy[0], camera_rpy[1], camera_rpy[2])
    
    #rot = np.matmul(camera_rot, craft_rot) # combine craft and camera rotation
    #rpy = rot2euler(camera_rot) * 180 / np.pi
    print('craft rpy is: ', craft_rpy * 180 / np.pi)
    print('camera rpy is: ', camera_rpy * 180 / np.pi)