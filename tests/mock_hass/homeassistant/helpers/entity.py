class Entity:
    _attr_supported_features = 0

    @property
    def supported_features(self):
        return self._attr_supported_features

    _attr_device_class = None

    @property
    def device_class(self):
        return self._attr_device_class
    
class DeviceInfo:
    pass
