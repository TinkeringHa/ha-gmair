from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_LIGHT
from .coordinator import GmairCoordinator
from .entity import GmairEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: GmairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GmairLight(coordinator, machine) for machine in coordinator.machines
    )


class GmairLight(GmairEntity, NumberEntity):
    _attr_name = "灯光亮度"
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_LIGHT
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:brightness-6"

    def __init__(self, coordinator: GmairCoordinator, machine: dict[str, Any]) -> None:
        super().__init__(coordinator, machine)
        self._attr_unique_id = f"{DOMAIN}_{self._qrcode}_light"

    @property
    def native_value(self) -> float | None:
        value = self._status.get("light")
        return float(value) if isinstance(value, int) else None

    async def async_set_native_value(self, value: float) -> None:
        await self._async_set_light(int(value))
