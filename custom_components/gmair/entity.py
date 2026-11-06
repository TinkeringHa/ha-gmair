from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, WEB_URL
from .coordinator import GmairCoordinator


class GmairEntity(CoordinatorEntity[GmairCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: GmairCoordinator, machine: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._machine = machine
        self._qrcode = machine["codeValue"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._qrcode)},
            name=machine.get("bindName") or self._qrcode,
            manufacturer="GMAIR",
            model=machine.get("modelName"),
            model_id=machine.get("modelId"),
            configuration_url=WEB_URL,
        )

    @property
    def _status(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self._qrcode) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._status)

    async def _async_operate(self, key: str, value: str) -> None:
        await self.coordinator.api.async_operate(self._qrcode, key, value)
        await self.coordinator.async_request_refresh()

    async def _async_set_light(self, value: int) -> None:
        await self.coordinator.api.async_set_light(self._qrcode, value)
        await self.coordinator.async_request_refresh()

    async def _async_set_speed(self, value: int) -> None:
        await self.coordinator.api.async_set_speed(self._qrcode, value)
        await self.coordinator.async_request_refresh()
