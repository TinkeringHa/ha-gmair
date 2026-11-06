from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HEAT_TO_NAME,
    MODE_TO_NAME,
    NAME_TO_HEAT,
    NAME_TO_MODE,
)
from .coordinator import GmairCoordinator
from .entity import GmairEntity

OPTIONS: tuple[tuple[str, str, dict], ...] = (
    ("mode", "模式", MODE_TO_NAME, NAME_TO_MODE),
    ("heat", "辅热", HEAT_TO_NAME, NAME_TO_HEAT),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: GmairCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GmairSelect(coordinator, machine, key, name, to_name, to_command)
        for machine in coordinator.machines
        for key, name, to_name, to_command in OPTIONS
    ]
    async_add_entities(entities)


class GmairSelect(GmairEntity, SelectEntity):
    def __init__(
        self,
        coordinator: GmairCoordinator,
        machine: dict[str, Any],
        key: str,
        name: str,
        to_name: dict[int, str],
        to_command: dict[str, str],
    ) -> None:
        super().__init__(coordinator, machine)
        self._key = key
        self._to_name = to_name
        self._to_command = to_command
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{self._qrcode}_{key}"
        self._attr_options = list(to_name.values())

    @property
    def current_option(self) -> str | None:
        value = self._status.get(self._key)
        if isinstance(value, int):
            return self._to_name.get(value)
        return None

    async def async_select_option(self, option: str) -> None:
        command = self._to_command.get(option)
        if command:
            await self._async_operate(self._key, command)
