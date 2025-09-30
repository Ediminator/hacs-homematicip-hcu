# custom_components/hcu_integration/config_flow.py
"""
Config flow for the Homematic IP Local (HCU) integration.

This file manages the user interface for setting up the integration (Config Flow)
and for changing its settings after setup (Options Flow).
"""
import logging
import aiohttp
import asyncio
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

# Import the HcuApiClient to resolve linter warnings and for type hinting.
from .api import HcuApiClient
from .const import (
    DOMAIN, HCU_AUTH_PORT, PLUGIN_ID, PLUGIN_FRIENDLY_NAME, CONF_PIN, 
    CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
)

_LOGGER = logging.getLogger(__name__)


class HcuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Homematic IP HCU Integration."""
    # The version of the config flow, used for future migrations.
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.host: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "HcuOptionsFlowHandler":
        """Get the options flow for this handler."""
        return HcuOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step where the user provides the HCU IP address."""
        if user_input is not None:
            self.host = user_input[CONF_HOST]
            # Use the host IP as the unique ID for the integration instance to prevent duplicates.
            await self.async_set_unique_id(self.host)
            self._abort_if_unique_id_configured()
            # Proceed to the authentication step.
            return await self.async_step_auth()
        
        # Show the initial form to the user.
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=self.context.get("host", "")): str})
        )

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Handle the authentication handshake with the HCU.
        This implements the two-step process described in the API documentation.
        """
        errors = {}
        if user_input is not None:
            activation_key = user_input["activation_key"]
            session = aiohttp_client.async_get_clientsession(self.hass)
            
            try:
                # Step 1: Request the auth token using the activation key.
                auth_token = await self._async_get_auth_token(session, self.host, activation_key)
                # Step 2: Confirm the auth token to finalize the client registration on the HCU.
                await self._async_confirm_auth_token(session, self.host, activation_key, auth_token)
                
                _LOGGER.info("Successfully received and confirmed auth token from HCU at %s", self.host)
                # Create the config entry in Home Assistant with the host and token.
                return self.async_create_entry(
                    title="Homematic IP HCU",
                    data={CONF_HOST: self.host, CONF_TOKEN: auth_token},
                )

            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Handshake failed, likely due to an invalid or expired key.")
                errors["base"] = "invalid_key"
        
        # Show the form asking for the activation key, with instructions.
        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({vol.Required("activation_key"): str}),
            description_placeholders={"hcu_ip": self.host},
            errors=errors,
        )

    async def _async_get_auth_token(self, session: aiohttp.ClientSession, host: str, key: str) -> str:
        """Request the API auth token from the HCU (Step 1 of authentication)."""
        url = f"https://{host}:{HCU_AUTH_PORT}/hmip/auth/requestConnectApiAuthToken"
        headers = {"VERSION": "12"}
        body = {
            "activationKey": key, 
            "pluginId": PLUGIN_ID,
            "friendlyName": PLUGIN_FRIENDLY_NAME
        }
        
        async with session.post(url, headers=headers, json=body, ssl=False) as response:
            response.raise_for_status()
            data = await response.json()
            if not (token := data.get("authToken")):
                raise ValueError("No authToken in HCU response")
            return token

    async def _async_confirm_auth_token(self, session: aiohttp.ClientSession, host: str, key: str, token: str) -> None:
        """Confirm the auth token with the HCU (Step 2 of authentication)."""
        url = f"https://{host}:{HCU_AUTH_PORT}/hmip/auth/confirmConnectApiAuthToken"
        headers = {"VERSION": "12"}
        body = {"activationKey": key, "authToken": token}

        async with session.post(url, headers=headers, json=body, ssl=False) as response:
            response.raise_for_status()
            if not (await response.json()).get("clientId"):
                raise ValueError("HCU did not confirm the authToken.")


class HcuOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for the HCU integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options for the integration."""
        if user_input is not None:
            # Save the user's input as the new options.
            return self.async_create_entry(title="", data=user_input)
        
        # Retrieve the coordinator to access the API client and its state.
        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
        # Add a type hint for the client to help the linter and for clarity.
        client: HcuApiClient | None = coordinator.client if coordinator else None
        third_party_oems = set()
        
        if client and client.state:
            # Find all third-party manufacturers to create toggles for them.
            for device in client.state.get("devices", {}).values():
                if (oem := device.get("oem")) and oem != "eQ-3":
                    third_party_oems.add(oem)

        # Build the options form schema dynamically.
        schema = {
            # Add an optional field for the Lock Authorization PIN.
            vol.Optional(
                CONF_PIN, 
                description={"suggested_value": self.config_entry.options.get(CONF_PIN)},
            ): str,
            # Add the field for the default comfort temperature.
            vol.Optional(
                CONF_COMFORT_TEMPERATURE,
                description={"suggested_value": self.config_entry.options.get(CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE)},
            ): vol.Coerce(float),
        }
        
        # Dynamically add toggles to enable/disable support for third-party devices.
        for oem in sorted(list(third_party_oems)):
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            schema[vol.Required(
                option_key, 
                default=self.config_entry.options.get(option_key, True)
            )] = bool

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))