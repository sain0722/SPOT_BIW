import json
import os

import DefineGlobal


class SpotDataManager:
    def __init__(self):
        self.fname_json_file = os.path.join(DefineGlobal.SPOT_DATA_PATH, DefineGlobal.SPOT_DATA_FILE_NAME)
        with open(self.fname_json_file, 'r', encoding='utf-8') as file:
            self.spot_data = json.load(file)

    # Getters
    def get_spot_setting(self, key):
        self.update_data()
        return self.spot_data.get("spot_settings", {}).get(key, None)

    def get_spot_connection_info(self):
        self.update_data()
        return self.spot_data.get("spot_settings", {}).get("connection", None)

    def get_control_params(self):
        self.update_data()
        return self.spot_data.get("spot_settings", {}).get("control_params", {})

    def get_inspection_settings(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {})

    def get_position_setting(self, position):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get(f"position{position}", {})

    def get_arm_setting(self, position):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get(f"position{position}", {}).get("arm_position")

    def get_waypoint_home(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get("home", {}).get("waypoint")

    def get_waypoint(self, position):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get(f"position{position}", {}).get("waypoint")

    def get_hole_waypoint(self):
        self.update_data()
        position2_setting = self.spot_data.get("inspection_settings", {}).get(f"position2", {})
        waypoint1 = position2_setting.get("waypoint1", "-")
        waypoint2 = position2_setting.get("waypoint2", "-")

        return waypoint1, waypoint2

    def get_waypoint_complete(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get("complete", {}).get("waypoint")

    def get_position2_settings(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get("position2", {})

    def get_arm_setting_2(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get("position2", {}).get("arm_position")

    def get_position3_settings(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get("position3", {})

    def get_arm_setting_3(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get("position3", {}).get("arm_position")

    def get_focus_absolute(self, position):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get(f"position{position}", {}).get("focus_absolute")

    def get_hole_inspection_setting(self):
        self.update_data()
        return self.spot_data.get("inspection_settings", {}).get("hole_inspection", {})

    def get_template_path(self):
        self.update_data()
        return self.spot_data.get("inspection_settings").get("hole_inspection").get("template_image_path")

    def get_arm_calibration_data(self):
        self.update_data()
        return self.spot_data.get("inspection_settings").get("hole_inspection").get("arm_correction_data")

    def get_arm_correction_path(self):
        self.update_data()
        return self.spot_data.get("inspection_settings").get("hole_inspection").get("arm_correction_data").get("path")

    def get_depth_settings(self):
        self.update_data()
        return self.spot_data.get("depth_settings", {})

    # Setters
    def set_spot_setting(self, key, value):
        self.spot_data["spot_settings"][key] = value
        self.save_data()

    def set_control_params(self, params):
        self.spot_data["spot_settings"]["control_params"] = params
        self.save_data()

    def set_spot_body_speed(self, body_speed):
        self.spot_data["spot_settings"]["control_params"]["body_speed"] = body_speed
        self.save_data()

    def set_spot_arm_speed(self, arm_speed):
        self.spot_data["spot_settings"]["control_params"]["arm_speed"] = arm_speed
        self.save_data()

    def set_position1_settings(self, settings):
        self.spot_data["inspection_settings"]["position1"] = settings
        self.save_data()

    def set_position2_settings(self, settings):
        self.spot_data["inspection_settings"]["position2"] = settings
        self.save_data()

    def set_position3_settings(self, settings):
        self.spot_data["inspection_settings"]["position3"] = settings
        self.save_data()

    def set_position_settings(self, settings, position):
        self.spot_data["inspection_settings"][f"position{position}"] = settings
        self.save_data()

    def set_arm_pose_setting(self, setting, position):
        self.spot_data["inspection_settings"][f"position{position}"]["arm_position"] = setting
        self.save_data()

    def set_inspection_settings(self, settings):
        self.spot_data["inspection_settings"] = settings
        self.save_data()

    def set_depth_settings(self, settings):
        self.spot_data["depth_settings"] = settings
        self.save_data()

    def set_template_region(self, region):
        self.spot_data["inspection_settings"]["hole_inspection"]["region"] = region
        self.save_data()

    def save_data(self):
        self.fname_json_file = os.path.join(DefineGlobal.SPOT_DATA_PATH, DefineGlobal.SPOT_DATA_FILE_NAME)
        with open(self.fname_json_file, 'w') as file:
            json.dump(self.spot_data, file, indent=4)

    def update_data(self):
        self.fname_json_file = os.path.join(DefineGlobal.SPOT_DATA_PATH, DefineGlobal.SPOT_DATA_FILE_NAME)

        if not os.path.exists(self.fname_json_file):
            with open(self.fname_json_file, 'w') as file:
                json.dump({}, file, indent=4)

        with open(self.fname_json_file, 'r', encoding='utf-8') as file:
            self.spot_data = json.load(file)
