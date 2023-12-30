"""Config flow for Smartoilgauge integration."""
from __future__ import annotations

import logging
from typing import Any
import httpx

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.httpx_client import get_async_client
import homeassistant.helpers.config_validation as cv

from aiosmartoilgauge import SmartOilGaugeClient

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smartoilgauge."""

    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self._api: SmartOilGaugeClient = None
        self._sensors = {}
        self.data = None

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            self._api = SmartOilGaugeClient(user_input[CONF_CLIENT_ID], user_input[CONF_CLIENT_SECRET], get_async_client(self.hass))
            if await self._api.async_login():
                device_data = await self._api.async_get_tank_data()
                self._sensors = {
                    '-'.join(dev.sensor_ids): "Tank " + str(dev.tank_number)
                    for dev in device_data
                }
                self.data = user_input
                return await self.async_step_devices()
            else:
                errors["base"] = "invalid_auth"
        except httpx.ConnectTimeout:
            errors["base"] = "cannot_connect"
        except httpx.HTTPStatusError as ex:
            if ex.response.status_code == 400:
                errors["base"] = "invalid_auth"
            else:
                errors["base"] = "unknown"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_devices(self, user_input: dict[str, Any] | None = None):
        """Handle sensor selection step."""
        if user_input is None:
            return self.async_show_form(
                step_id="devices",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            "sensors", default=list(self._sensors)
                        ): cv.multi_select(self._sensors)
                    }
                ),
            )
        else:
            self.data.update(user_input)
            return self.async_create_entry(
                title="Smart Oil Gauge", data=self.data
            )
