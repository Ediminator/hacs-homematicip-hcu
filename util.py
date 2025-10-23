# custom_components/hcu_integration/util.py
import ssl
from homeassistant.core import HomeAssistant

async def create_unverified_ssl_context(hass: HomeAssistant) -> ssl.SSLContext:
    """Create an SSL context that does not verify certificates, in a non-blocking way."""

    def _create_context():
        """The actual SSL context creation to run in executor."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    return await hass.async_add_executor_job(_create_context)