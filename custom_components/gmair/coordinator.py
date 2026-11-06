import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GmairApi, GmairError
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class GmairCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: GmairApi,
        machines: list[dict[str, Any]],
        city_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.api = api
        self.machines = machines
        self.city_id = city_id
        self.air: dict[str, Any] = {}
        self.filters: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        try:
            for machine in self.machines:
                qrcode = machine["codeValue"]
                result[qrcode] = await self.api.async_get_status(qrcode)
        except GmairError as err:
            raise UpdateFailed(str(err)) from err

        for machine in self.machines:
            qrcode = machine["codeValue"]
            try:
                self.filters[qrcode] = await self.api.async_get_filter_state(qrcode)
            except GmairError as err:
                _LOGGER.debug("filter state for %s failed: %s", qrcode, err)

        try:
            self.air = await self.api.async_get_air_quality(self.city_id)
        except GmairError as err:
            _LOGGER.debug("air quality for %s failed: %s", self.city_id, err)

        return result
