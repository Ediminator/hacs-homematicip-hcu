# custom_components/hcu_integration/config_flow.py
"""Config flow for Homematic IP Local (HCU) integration."""
import logging
import aiohttp
import asyncio
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_PORT = 6969
PLUGIN_ID = "de.homeassistant.hcu.integration"
CONF_PIN = "pin"

class HcuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for the Homematic IP HCU Integration.

    This flow guides the user through a two-step process:
    1.  `async_step_user`: Gathers the HCU's IP address.
    2.  `async_step_auth`: Gathers a temporary activation key from the user
        and performs the two-part authentication handshake with the HCU to
        obtain a permanent authorization token.
    """
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.host = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "HcuOptionsFlowHandler":
        """Get the options flow for this handler."""
        return HcuOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step to get the HCU IP address."""
        if user_input is not None:
            self.host = user_input[CONF_HOST]
            await self.async_set_unique_id(self.host)
            self._abort_if_unique_id_configured()
            return await self.async_step_auth()
        
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({vol.Required(CONF_HOST): str})
        )

    async def async_step_auth(self, user_input: dict | None = None) -> FlowResult:
        """Handle the authentication step where the user provides the activation key."""
        errors = {}
        if user_input is not None:
            activation_key = user_input["activation_key"]
            session = aiohttp_client.async_get_clientsession(self.hass)
            
            try:
                # Step 1 of Handshake: Request the preliminary auth token from the HCU.
                request_url = f"https://{self.host}:{AUTH_PORT}/hmip/auth/requestConnectApiAuthToken"
                headers = {"VERSION": "12"}
                body = {
                    "activationKey": activation_key, "pluginId": PLUGIN_ID,
                    "friendlyName": {"de": "Home Assistant Integration", "en": "Home Assistant Integration"}
                }
                
                async with session.post(request_url, headers=headers, json=body, ssl=False) as response:
                    response.raise_for_status()
                    data = await response.json()
                    auth_token = data.get("authToken")

                # Step 2 of Handshake: Confirm the auth token to make it permanent.
                confirm_url = f"https://{self.host}:{AUTH_PORT}/hmip/auth/confirmConnectApiAuthToken"
                confirm_body = {"activationKey": activation_key, "authToken": auth_token}
                
                async with session.post(confirm_url, headers=headers, json=confirm_body, ssl=False) as response:
                    response.raise_for_status()
                    if not (await response.json()).get("clientId"):
                        raise ValueError("HCU did not confirm the authToken.")

                _LOGGER.info("Successfully received and confirmed auth token from HCU")
                return self.async_create_entry(
                    title="Homematic IP HCU",
                    data={CONF_HOST: self.host, CONF_TOKEN: auth_token}
                )

            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Handshake failed")
                errors["base"] = "invalid_key"

        # Show the form with instructions and an image (via strings.json).
        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({vol.Required("activation_key"): str}),
            description_placeholders={"hcu_ip": self.host},
            errors=errors,
        )

class HcuOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for the HCU integration to configure things like the lock PIN."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Show the form to the user to enter the PIN.
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_PIN, default=self.config_entry.options.get(CONF_PIN, "")): str,
            }),
        )