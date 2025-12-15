class HomeAssistant:
    pass

class Callback:
    pass

class ServiceCall:
    def __init__(self, data):
        self.data = data

def split_entity_id(entity_id):
    return entity_id.split(".", 1)

def callback(func):
    return func

