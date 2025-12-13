# custom_components/hcu_integration/util.py
import ssl
from homeassistant.core import HomeAssistant

# Cache key for storing SSL context in hass.data
_SSL_CONTEXT_CACHE_KEY = "hcu_integration_ssl_context"

async def create_unverified_ssl_context(hass: HomeAssistant) -> ssl.SSLContext:
    """Create an SSL context that does not verify certificates, in a non-blocking way.

    The SSL context is cached in hass.data to avoid recreating it on every call.
    """
    # Check if SSL context is already cached
    if _SSL_CONTEXT_CACHE_KEY in hass.data:
        return hass.data[_SSL_CONTEXT_CACHE_KEY]

    def _create_context() -> ssl.SSLContext:
        """The actual SSL context creation to run in executor."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    # Create and cache the context
    context = await hass.async_add_executor_job(_create_context)
    hass.data[_SSL_CONTEXT_CACHE_KEY] = context
    return context


def get_device_manufacturer(device_data: dict) -> str:
    """Determine the manufacturer of a device.

    Corrects cases where 3rd party devices (like Philips Hue) are reported as 'eQ-3'.
    """
    # 1. Trust explicit OEM if it's not the default "eQ-3"
    oem = device_data.get("oem")
    if oem and oem != "eQ-3":
        return oem

    # 2. Check Plugin ID (Strongest Signal for external devices)
    plugin_id = device_data.get("pluginId")
    if plugin_id == "de.eq3.plugin.hue":
        return "Philips Hue"
        
    # 3. Check Device Type/Archetype for generic "External" status
    # "PLUGIN_EXTERNAL" strongly implies a 3rd party integration
    if device_data.get("type") == "PLUGIN_EXTERNAL":
        return "3rd Party"

    # 4. Heuristics based on model type (Fallback)
    model_type = device_data.get("modelType", "")
    
    if "Hue" in model_type:
        return "Philips Hue"
    
    # 5. Check for standard Homematic IP prefix
    if model_type.startswith("HmIP-") or model_type.startswith("HM-") or model_type.startswith("ALPHA-"):
        return "eQ-3"
        
    # 6. Default
    # If it has no 'oem' field and didn't match above, we assume it's a standard device 
    # (or legacy one) and return "eQ-3" to match previous behavior
    return "eQ-3"
