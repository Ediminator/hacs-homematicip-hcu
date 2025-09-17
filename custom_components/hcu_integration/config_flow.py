# custom_components/hcu_integration/config_flow.py
"""Config flow for Homematic IP Local (HCU) integration."""
import logging
import aiohttp
import asyncio
import ssl
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_PORT = 6969
PLUGIN_ID = "de.homeassistant.hcu.integration"


@config_entries.HANDLERS.register(DOMAIN)
class HcuConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Homematic IP HCU Integration."""
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.host = None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step to get the HCU IP address."""
        if user_input is not None:
            self.host = user_input[CONF_HOST]
            await self.async_set_unique_id(self.host)
            self._abort_if_unique_id_configured()
            return await self.async_step_auth()

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str
        })
        
        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema,
        )

    async def async_step_auth(self, user_input: dict | None = None) -> FlowResult:
        """Handle the authentication step where the user provides the activation key."""
        errors = {}
        if user_input is not None:
            activation_key = user_input["activation_key"]
            session = aiohttp_client.async_get_clientsession(self.hass)
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            try:
                # Step 1 of Handshake: Request the preliminary auth token
                _LOGGER.debug("Requesting auth token with activation key")
                request_url = f"https://{self.host}:{AUTH_PORT}/hmip/auth/requestConnectApiAuthToken"
                headers = {"VERSION": "12"}
                body = {
                    "activationKey": activation_key,
                    "pluginId": PLUGIN_ID,
                    "friendlyName": {"de": "Home Assistant Integration", "en": "Home Assistant Integration"}
                }
                
                async with session.post(request_url, headers=headers, json=body, ssl=ssl_context) as response:
                    response.raise_for_status()
                    data = await response.json()
                    auth_token = data.get("authToken")
                    if not auth_token:
                        raise ValueError("HCU did not return an authToken.")

                # Step 2 of Handshake: Confirm the auth token
                _LOGGER.debug("Confirming the received auth token")
                confirm_url = f"https://{self.host}:{AUTH_PORT}/hmip/auth/confirmConnectApiAuthToken"
                confirm_body = {"activationKey": activation_key, "authToken": auth_token}
                
                async with session.post(confirm_url, headers=headers, json=confirm_body, ssl=ssl_context) as response:
                    response.raise_for_status()
                    confirm_data = await response.json()
                    if not confirm_data.get("clientId"):
                        raise ValueError("HCU did not confirm the authToken.")

                _LOGGER.info("Successfully received and confirmed auth token from HCU")
                return self.async_create_entry(
                    title="Homematic IP Home Control Unit",
                    data={CONF_HOST: self.host, CONF_TOKEN: auth_token}
                )

            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error(f"Handshake failed: {e}")
                errors["base"] = "invalid_key"

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({vol.Required("activation_key"): str}),
            description_placeholders={"hcu_ip": self.host},
            errors=errors,
        )