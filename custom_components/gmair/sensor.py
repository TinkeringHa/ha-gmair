from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfDensity,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FILTER_STATUS_TO_NAME
from .coordinator import GmairCoordinator
from .entity import GmairEntity


@dataclass(frozen=True, kw_only=True)
class GmairSensorDescription(SensorEntityDescription):
    field: str
    source: str = "status"


SENSORS: tuple[GmairSensorDescription, ...] = (
    GmairSensorDescription(
        key="pm25",
        field="pm2_5",
        name="室内 PM2.5",
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GmairSensorDescription(
        key="co2",
        field="co2",
        name="CO2",
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GmairSensorDescription(
        key="temperature",
        field="temperature",
        name="温度",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GmairSensorDescription(
        key="humidity",
        field="humidity",
        name="湿度",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GmairSensorDescription(
        key="volume",
        field="volume",
        name="风量",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-windy",
    ),
    GmairSensorDescription(
        key="air_city",
        field="cityName",
        name="所在城市",
        source="air",
        icon="mdi:map-marker",
    ),
    GmairSensorDescription(
        key="air_aqi",
        field="aqi",
        name="室外 AQI",
        source="air",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-cloudy",
    ),
    GmairSensorDescription(
        key="air_pm25",
        field="pm2_5",
        name="室外 PM2.5",
        source="air",
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GmairSensorDescription(
        key="filter_clean",
        field="isNeedClean",
        name="初滤网",
        source="filter",
        icon="mdi:air-filter",
    ),
    GmairSensorDescription(
        key="filter_replace",
        field="replaceStatus",
        name="主滤网",
        source="filter",
        icon="mdi:air-filter",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: GmairCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GmairSensor(coordinator, machine, description)
        for machine in coordinator.machines
        for description in SENSORS
    ]
    async_add_entities(entities)


class GmairSensor(GmairEntity, SensorEntity):
    entity_description: GmairSensorDescription

    def __init__(
        self,
        coordinator: GmairCoordinator,
        machine: dict[str, Any],
        description: GmairSensorDescription,
    ) -> None:
        super().__init__(coordinator, machine)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{self._qrcode}_{description.key}"

    @property
    def native_value(self) -> Any:
        source = self.entity_description.source
        if source == "air":
            container = self.coordinator.air
        elif source == "filter":
            container = self.coordinator.filters.get(self._qrcode) or {}
        else:
            container = self._status

        value = container.get(self.entity_description.field)
        if value is None:
            return None
        if self.entity_description.key == "filter_clean":
            return "需要清洗" if value else "正常"
        if self.entity_description.key == "filter_replace":
            return FILTER_STATUS_TO_NAME.get(value, value)
        if self.entity_description.key in ("air_aqi", "air_pm25"):
            return round(value)
        return value
