class MockConfigEntry:
    def __init__(self, domain, unique_id, data, entry_id="test"):
        self.domain = domain
        self.unique_id = unique_id
        self.data = data
        self.entry_id = entry_id
        
    def add_to_hass(self, hass):
        pass
