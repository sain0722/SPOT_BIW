from datetime import datetime
from enum import Enum

import numpy as np

class InspectionDataManager:
    def __init__(self):
        self.timestamp = None

        self.position1_image = None
        self.position2_image = None
        self.position3_image = None

        self.position1_data = None
        self.position2_data = None
        self.position3_data = None

    def clear(self):
        self.timestamp = None
        self.position1_image = None
        self.position2_image = None
        self.position3_image = None

        self.position1_data = None
        self.position2_data = None
        self.position3_data = None

    def set_position1_data(self, image: np.ndarray, data):
        self.position1_image = image
        self.position1_data = data

    def set_position2_data(self, image: np.ndarray, data):
        self.position2_image = image
        self.position2_data = data

    def set_position3_data(self, image: np.ndarray, data):
        self.position3_image = image
        self.position3_data = data

    def get_inspection_image(self, position):
        image = None
        if position == 1:
            image = self.position1_image
        elif position == 2:
            image = self.position2_image
        elif position == 3:
            image = self.position3_image

        return image

    def get_inspection_data(self, position):
        data = None
        if position == 1:
            data = self.position1_data
        elif position == 2:
            data = self.position2_data
        elif position == 3:
            data = self.position3_data

        return data
