import json
import os

import DefineGlobal

path = DefineGlobal.SPOT_DATA_PATH
fname = DefineGlobal.SPOT_DATA_FILE_NAME

def read_arm_correction():
    with open(os.path.join(path, fname), "r", encoding='utf-8') as file:
        spot_data = json.load(file)

    return spot_data['inspection_settings']['hole_inspection']['arm_correction_data']


def read_hole_inspection_data():
    with open(os.path.join(path, fname), "r", encoding='utf-8') as file:
        spot_data = json.load(file)

    return spot_data['inspection_settings']['hole_inspection']


def read_depth_setting():
    with open(os.path.join(path, fname), "r", encoding='utf-8') as file:
        spot_data = json.load(file)

    return spot_data['depth_settings']
