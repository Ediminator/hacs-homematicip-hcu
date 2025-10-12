# custom_components/hcu_integration/config_flow.py
"""Config flow for the Homematic IP Local (HCU) integration."""
import logging
import aiohttp
import asyncio
import voluptuous as vol
from typing import Any, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import callback, HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client, device_registry as dr

from .api import HcuApiClient, HcuApiError
from .const import (
    DOMAIN,
    DEFAULT_HCU_AUTH_PORT,
    DEFAULT_HCU_WEBSOCKET_PORT,
    PLUGIN_ID,
    PLUGIN_FRIENDLY_NAME,
    CONF_PIN,
    CONF_COMFORT_TEMPERATURE,
    DEFAULT_COMFORT_TEMPERATURE,
    CONF_AUTH_PORT,
    CONF_WEBSOCKET_PORT,
)
from .util import create_unverified_ssl_context

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the HCU component."""
    # This is a no-op, but required for the async_will_remove_config_entry hook to work.
    return True


async def async_will_remove_config_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """
    Handle removal of a config entry.

    This function is called by Home Assistant just before an integration entry is
    removed. It logs a warning to guide the user on how to manually revoke the
    orphaned API token on their HCU for security purposes, as there is no API
    endpoint available to do this programmatically.
    """
    _LOGGER.warning(
        "The HCU integration has been removed. For security, please manually delete the "
        "'Home Assistant Integration' client from your Homematic IP smartphone app "
        "or HCUweb to revoke the old API token."
    )


class HcuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Homematic IP HCU Integration."""

    VERSION = 1
    reauth_entry: ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> "HcuOptionsFlowHandler":
        """Get the options flow for this handler."""
        return HcuOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step where the user provides the host and ports."""
        if user_input is not None:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})
            # Pass all user input to the auth step
            return await self.async_step_auth(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.context.get("host", "")): str,
                    vol.Required(CONF_AUTH_PORT, default=DEFAULT_HCU_AUTH_PORT): int,
                    vol.Required(CONF_WEBSOCKET_PORT, default=DEFAULT_HCU_WEBSOCKET_PORT): int,
                }
            ),
        )

    async def async_step_auth(
        self, user_input: dict[str, Any]
    ) -> FlowResult:
        """
        Handle the authentication step where the user provides an activation key.
        This step communicates with the HCU to acquire a long-lived auth token.
        """
        errors = {}
        host = user_input[CONF_HOST]
        auth_port = user_input[CONF_AUTH_PORT]

        if "activation_key" in user_input:
            activation_key = user_input["activation_key"]
            session = aiohttp_client.async_get_clientsession(self.hass)
            ssl_context = await create_unverified_ssl_context(self.hass)

            try:
                auth_token = await self._async_get_auth_token(
                    session, host, auth_port, activation_key, ssl_context
                )
                await self._async_confirm_auth_token(
                    session, host, auth_port, activation_key, auth_token, ssl_context
                )

                _LOGGER.info(
                    "Successfully received and confirmed auth token from HCU at %s",
                    host,
                )
                
                # Create a new entry for a fresh installation
                return self.async_create_entry(
                    title="Homematic IP Local (HCU)",
                    data={
                        CONF_HOST: host,
                        CONF_AUTH_PORT: auth_port,
                        CONF_WEBSOCKET_PORT: user_input[CONF_WEBSOCKET_PORT],
                        CONF_TOKEN: auth_token
                    },
                )

            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception(
                    "Handshake failed, likely due to an invalid or expired key."
                )
                errors["base"] = "invalid_key"

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({vol.Required("activation_key"): str}),
            description_placeholders={"hcu_ip": host},
            errors=errors,
        )
    
    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Handle a reauthentication flow.
        This is triggered by Home Assistant when the integration reports that
        reauthentication is needed (e.g., due to an invalid PIN).
        """
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Handle the PIN reauthentication form.
        This step securely updates the PIN in the config entry's data.
        """
        if user_input is not None:
            new_data = {**self.reauth_entry.data, CONF_PIN: user_input[CONF_PIN]}
            self.hass.config_entries.async_update_entry(self.reauth_entry, data=new_data)
            await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PIN): str}),
        )


    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a reconfiguration flow for changing HCU connection details."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors = {}

        if user_input is not None:
            new_host = user_input[CONF_HOST]
            new_auth_port = user_input[CONF_AUTH_PORT]
            new_websocket_port = user_input[CONF_WEBSOCKET_PORT]

            try:
                # Test the connection to the new host/ports with the existing token.
                session = aiohttp_client.async_get_clientsession(self.hass)
                client = HcuApiClient(
                    self.hass,
                    new_host,
                    entry.data[CONF_TOKEN],
                    session,
                    new_auth_port,
                    new_websocket_port,
                )
                await client.get_system_state()

                # If successful, update the config entry's data.
                self.hass.config_entries.async_update_entry(
                    entry, data={
                        **entry.data,
                        CONF_HOST: new_host,
                        CONF_AUTH_PORT: new_auth_port,
                        CONF_WEBSOCKET_PORT: new_websocket_port,
                    }
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

            except (HcuApiError, ConnectionError, asyncio.TimeoutError, aiohttp.ClientConnectorError):
                _LOGGER.error("Failed to connect to new HCU host/port combination")
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reconfiguration.")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                    vol.Required(CONF_AUTH_PORT, default=entry.data.get(CONF_AUTH_PORT, DEFAULT_HCU_AUTH_PORT)): int,
                    vol.Required(CONF_WEBSOCKET_PORT, default=entry.data.get(CONF_WEBSOCKET_PORT, DEFAULT_HCU_WEBSOCKET_PORT)): int,
                }
            ),
            errors=errors,
        )

    async def _async_get_auth_token(
        self, session: aiohttp.ClientSession, host: str, port: int, key: str, ssl_context
    ) -> str:
        """Request a new auth token from the HCU."""
        url = f"https://{host}:{port}/hmip/auth/requestConnectApiAuthToken"
        headers = {"VERSION": "12"}
        body = {
            "activationKey": key,
            "pluginId": PLUGIN_ID,
            "friendlyName": PLUGIN_FRIENDLY_NAME,
        }

        async with session.post(
            url, headers=headers, json=body, ssl=ssl_context
        ) as response:
            response.raise_for_status()
            data = await response.json()
            if not (token := data.get("authToken")):
                raise ValueError("No authToken in HCU response")
            return token

    async def _async_confirm_auth_token(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        key: str,
        token: str,
        ssl_context,
    ) -> None:
        """Confirm the new auth token with the HCU."""
        url = f"https://{host}:{port}/hmip/auth/confirmConnectApiAuthToken"
        headers = {"VERSION": "12"}
        body = {"activationKey": key, "authToken": token}

        async with session.post(
            url, headers=headers, json=body, ssl=ssl_context
        ) as response:
            response.raise_for_status()
            if not (await response.json()).get("clientId"):
                raise ValueError("HCU did not confirm the authToken.")


class HcuOptionsFlowHandler(OptionsFlow):
    """Handle an options flow for the HCU integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options for the integration."""
        if user_input is not None:
            await self._handle_device_removal(user_input)
            # Merge existing options with the new ones provided by the user.
            new_options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        coordinator: "HcuCoordinator" | None = self.hass.data[DOMAIN].get(
            self.config_entry.entry_id
        )
        client: HcuApiClient | None = coordinator.client if coordinator else None
        third_party_oems = set()

        if client and client.state:
            for device in client.state.get("devices", {}).values():
                if (oem := device.get("oem")) and oem != "eQ-3":
                    third_party_oems.add(oem)

        schema = {
            vol.Optional(
                CONF_COMFORT_TEMPERATURE,
                default=self.config_entry.options.get(
                    CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
                ),
            ): vol.Coerce(float),
        }

        # Dynamically add boolean toggles for each third-party OEM found.
        for oem in sorted(list(third_party_oems)):
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            schema[
                vol.Required(
                    option_key,
                    default=self.config_entry.options.get(option_key, True),
                )
            ] = bool

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))

    async def _handle_device_removal(self, user_input: dict[str, Any]) -> None:
        """Remove devices from the registry for OEMs that have been disabled."""
        device_registry = dr.async_get(self.hass)

        disabled_oems = set()
        for key, value in user_input.items():
            if key.startswith("import_") and not value:
                # Check if the option was previously enabled or non-existent
                if self.config_entry.options.get(key, True):
                    oem_name = key.replace("import_", "").replace("_", " ").title()
                    disabled_oems.add(oem_name)

        if not disabled_oems:
            return

        all_devices = dr.async_entries_for_config_entry(
            device_registry, self.config_entry.entry_id
        )

        for device in all_devices:
            if device.manufacturer in disabled_oems:
                _LOGGER.info(
                    "Removing device %s (%s) as its manufacturer (%s) has been disabled via options.",
                    device.name,
                    device.id,
                    device.manufacturer,
                )
                device_registry.async_remove_device(device.id)