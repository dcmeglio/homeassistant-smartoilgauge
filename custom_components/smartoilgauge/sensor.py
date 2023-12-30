from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfVolume

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartoilgaugeCoordinator
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
)

from aiosmartoilgauge import SmartOilGaugeClient, TankInfo


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, add_entities):
    """Setup the Beckettlink sensors."""
    coordinator: SmartoilgaugeCoordinator = hass.data[DOMAIN][config.entry_id]
    sensors = None

    try:
        sensors = await coordinator.load_sensor_data()
    except Exception as ex:
        raise ConfigEntryNotReady("Failed to retrieve devices") from ex

    entities = []
    for sensor in sensors:
        entities.append(
            SmartoilgaugeTankSensorEntity(
                hass=hass,
                name="Battery Level",
                device_class="battery",
                device_type="battery",
                device=sensor,
                coordinator=coordinator,
                entity_category=EntityCategory.DIAGNOSTIC,
            )
        )
        entities.append(
            SmartoilgaugeTankSensorEntity(
                hass=hass,
                name="Tank Level",
                device_class=None,
                device_type="tank_level",
                device=sensor,
                coordinator=coordinator,
                entity_category=None,
            )
        )
        entities.append(
            SmartoilgaugeTankSensorEntity(
                hass=hass,
                name="Tank Volume",
                device_class=None,
                device_type="tank_volume",
                device=sensor,
                coordinator=coordinator,
                entity_category=None,
            )
        )

    add_entities(entities)


class SmartoilgaugeTankSensorEntity(SensorEntity, CoordinatorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        device_type: str,
        device: TankInfo,
        coordinator: SmartoilgaugeCoordinator,
        device_class: str,
        entity_category: EntityCategory,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_has_entity_name = True
        self._coordinator = coordinator
        self._device = device

        self._device_type = device_type
        self._attr_entity_category = entity_category
        self._attr_unique_id = '-'.join(device.sensor_ids) + "_" + device_type

        if device_type == "battery":
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif device_type == "tank_level":
            self._attr_native_unit_of_measurement = UnitOfVolume.GALLONS
            self._attr_icon = "mdi:hydraulic-oil-level"
        elif device_type == "tank_volume":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_icon = "mdi:hydraulic-oil-level"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, '-'.join(device.sensor_ids))},
            manufacturer=MANUFACTURER,
            name="Tank " + str(device.tank_number),
            model=MODEL,
        )

    def _handle_coordinator_update(self) -> None:
        sensors = self.coordinator.get_sensors()
        sensor: TankInfo = next(x for x in sensors if '-'.join(x.sensor_ids) == '-'.join(self._device.sensor_ids))
        if self._device_type == "battery":
            if sensor.battery_level == "Excellent":
                battery_level = 100
            elif sensor.battery_level == "Good":
                battery_level = 75
            elif sensor.battery_level == "Fair":
                battery_level = 50
            elif sensor.battery_level == "Poor":
                battery_level = 25
            self._attr_native_value = battery_level
        elif self._device_type == "tank_level":
            self._attr_native_value = sensor.gallons_remaining
        elif self._device_type == "tank_volume":
            self._attr_native_value = (1 - (sensor.tank_volume-sensor.gallons_remaining)/sensor.tank_volume)*100
        self.async_write_ha_state()