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