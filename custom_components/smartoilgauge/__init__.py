"""The Smartoilgauge integration."""
from __future__ import annotations
from datetime import timedelta
import logging

from aiosmartoilgauge import SmartOilGaugeClient, TankInfo
import httpx

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.httpx_client import get_async_client

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smartoilgauge from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    client = SmartOilGaugeClient(entry.data.get(CONF_CLIENT_ID), entry.data.get(CONF_CLIENT_SECRET), get_async_client(hass))
    try:
        await client.async_login()
    except httpx.HTTPStatusError as ex:
        if ex.response.status_code == 400:
            raise ConfigEntryAuthFailed() from ex
        raise ConfigEntryNotReady() from ex
    except Exception as ex:
        raise ConfigEntryNotReady() from ex

    coordinator = SmartoilgaugeCoordinator(hass, client, entry)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await coordinator.async_config_entry_first_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SmartoilgaugeCoordinator(DataUpdateCoordinator):
    """Smartoilgauge coordinator."""

    def __init__(
        self, hass: HomeAssistant, api: SmartOilGaugeClient, entry: ConfigEntry, devices=None
    ):
        """Initialize Smartoilgauge coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Smartoilgauge",
            update_interval=timedelta(hours=2),
        )
        self.api: SmartOilGaugeClient = api
        self.hass: HomeAssistant = hass
        self.entry = entry
        self._sensors: [TankInfo] = None

    async def load_sensor_data(self) -> [TankInfo]:
        self._sensors = await self.api.async_get_tank_data()
        return self._sensors

    def get_sensors(self) -> [TankInfo]:
        """Get a list of device sensors."""
        return self._sensors

    async def _async_update_data(self) -> [TankInfo]:
        """Fetch data from API endpoint."""
        try:
            return await self.load_sensor_data()
        except Exception as ex:
            raise UpdateFailed() from ex
