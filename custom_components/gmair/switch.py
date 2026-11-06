from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GmairCoordinator
from .entity import GmairEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: GmairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GmairLock(coordinator, machine) for machine in coordinator.machines
    )


class GmairLock(GmairEntity, SwitchEntity):
    _attr_name = "童锁"
    _attr_icon = "mdi:lock"

    def __init__(self, coordinator: GmairCoordinator, machine: dict[str, Any]) -> None:
        super().__init__(coordinator, machine)
        self._attr_unique_id = f"{DOMAIN}_{self._qrcode}_lock"

    @property
    def is_on(self) -> bool:
        return self._status.get("lock") == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_operate("lock", "on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_operate("lock", "off")
