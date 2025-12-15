from enum import IntFlag

class CoverDeviceClass:
    SHUTTER = "shutter"
    BLIND = "blind"
    GARAGE = "garage"

class CoverEntityFeature(IntFlag):
    OPEN = 1
    CLOSE = 2
    SET_POSITION = 4
    STOP = 8
    OPEN_TILT = 16
    CLOSE_TILT = 32
    STOP_TILT = 64
    SET_TILT_POSITION = 128

class CoverEntity:
    _attr_device_class = None
    _attr_supported_features = 0
    _attr_assumed_state = False
    _attr_unique_id = None
    _attr_name = None
    _attr_has_entity_name = False
    _attr_translation_key = None
    
    @property
    def device_info(self):
        return {}
        
    def _set_entity_name(self, channel_label, feature_name=None):
        pass

ATTR_POSITION = "position"
ATTR_TILT_POSITION = "tilt_position"
