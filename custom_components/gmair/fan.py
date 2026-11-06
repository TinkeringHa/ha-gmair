from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_VOLUME, MIN_VOLUME
from .coordinator import GmairCoordinator
from .entity import GmairEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: GmairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GmairFan(coordinator, machine) for machine in coordinator.machines
    )


class GmairFan(GmairEntity, FanEntity):
    _attr_name = "新风机"
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
    )
    _attr_speed_count = 100

    def __init__(self, coordinator: GmairCoordinator, machine: dict[str, Any]) -> None:
        super().__init__(coordinator, machine)
        self._attr_unique_id = f"{DOMAIN}_{self._qrcode}_fan"

    @property
    def is_on(self) -> bool:
        return self._status.get("power") == 1

    @property
    def percentage(self) -> int | None:
        if not self.is_on:
            return 0
        volume = self._status.get("volume")
        if not isinstance(volume, int):
            return None
        if volume < MIN_VOLUME:
            return 1
        pct = round((volume - MIN_VOLUME) / (MAX_VOLUME - MIN_VOLUME) * 100)
        return max(1, min(100, pct))

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self._async_operate("power", "on")
        if percentage:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_operate("power", "off")

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage <= 0:
            await self.async_turn_off()
            return
        speed = round(MIN_VOLUME + percentage * (MAX_VOLUME - MIN_VOLUME) / 100)
        await self._async_set_speed(int(speed))
