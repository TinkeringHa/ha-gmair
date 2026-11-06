import logging
from typing import Any, Mapping

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import GmairApi, GmairAuthError, GmairError
from .const import (
    AUTH_PASSWORD,
    AUTH_SMS,
    CONF_AUTH_METHOD,
    CONF_CITY_ID,
    CONF_CODE,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
    DEFAULT_CITY_ID,
    DOMAIN,
    NAME,
)

_LOGGER = logging.getLogger(__name__)

MENU_OPTIONS = ["password", "sms"]

STEP_PASSWORD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_SMS_SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str})

STEP_SMS_CODE_SCHEMA = vol.Schema({vol.Required(CONF_CODE): str})


class GmairConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._username: str = ""
        self._auth_method: str = AUTH_PASSWORD
        self._session: aiohttp.ClientSession | None = None

    def _api(self) -> GmairApi:
        if self._session is None:
            self._session = async_create_clientsession(
                self.hass, cookie_jar=aiohttp.DummyCookieJar()
            )
        return GmairApi(self._session)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GmairOptionsFlow()

    async def _async_finish(self, data: dict[str, Any]) -> ConfigFlowResult:
        unique_id = f"gmair-{data[CONF_USERNAME]}"
        title = f"{NAME} ({data[CONF_USERNAME]})"
        if self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()
            return self.async_update_reload_and_abort(
                entry,
                data={**entry.data, **data},
                title=title,
            )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=MENU_OPTIONS)

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api = self._api()
            try:
                await api.async_login(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except GmairAuthError as err:
                _LOGGER.warning("gmair password login rejected: %s", err)
                errors["base"] = "invalid_auth"
            except GmairError as err:
                _LOGGER.warning("gmair password login error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("unexpected error during gmair login")
                errors["base"] = "unknown"
            else:
                try:
                    machines = await api.async_get_machines()
                except GmairError as err:
                    _LOGGER.warning("gmair machine list error: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    if not machines:
                        errors["base"] = "no_devices"
                    else:
                        return await self._async_finish(
                            {
                                CONF_USERNAME: user_input[CONF_USERNAME],
                                CONF_PASSWORD: user_input[CONF_PASSWORD],
                                CONF_AUTH_METHOD: AUTH_PASSWORD,
                            }
                        )

        return self.async_show_form(
            step_id="password",
            data_schema=self.add_suggested_values_to_schema(
                STEP_PASSWORD_SCHEMA, {CONF_USERNAME: self._username}
            ),
            errors=errors,
        )

    async def async_step_sms(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api = self._api()
            try:
                await api.async_request_code(user_input[CONF_USERNAME])
            except GmairAuthError:
                errors["base"] = "code_request_failed"
            except GmairError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("unexpected error during gmair code request")
                errors["base"] = "unknown"
            else:
                self._username = user_input[CONF_USERNAME].strip()
                self._auth_method = AUTH_SMS
                return await self.async_step_sms_code()

        return self.async_show_form(
            step_id="sms",
            data_schema=self.add_suggested_values_to_schema(
                STEP_SMS_SCHEMA, {CONF_USERNAME: self._username}
            ),
            errors=errors,
        )

    async def async_step_sms_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api = self._api()
            try:
                token = await api.async_login_with_code(
                    self._username, user_input[CONF_CODE]
                )
            except GmairAuthError as err:
                _LOGGER.warning("gmair sms code rejected: %s", err)
                errors["base"] = "invalid_code"
            except GmairError as err:
                _LOGGER.warning("gmair sms login error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("unexpected error during gmair code login")
                errors["base"] = "unknown"
            else:
                try:
                    machines = await api.async_get_machines()
                except GmairError as err:
                    _LOGGER.warning("gmair machine list error: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    if not machines:
                        errors["base"] = "no_devices"
                    else:
                        return await self._async_finish(
                            {
                                CONF_USERNAME: self._username,
                                CONF_TOKEN: token,
                                CONF_AUTH_METHOD: AUTH_SMS,
                            }
                        )

        return self.async_show_form(
            step_id="sms_code",
            data_schema=STEP_SMS_CODE_SCHEMA,
            errors=errors,
            description_placeholders={"phone": self._username},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        self._username = entry_data.get(CONF_USERNAME, "")
        self._auth_method = entry_data.get(CONF_AUTH_METHOD, AUTH_PASSWORD)
        if self._auth_method == AUTH_SMS:
            return await self.async_step_sms()
        return await self.async_step_password()


class GmairOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title="", data={CONF_CITY_ID: user_input[CONF_CITY_ID]}
            )

        options: dict[str, str] = {}
        try:
            api = GmairApi(
                async_create_clientsession(
                    self.hass, cookie_jar=aiohttp.DummyCookieJar()
                )
            )
            options = await api.async_get_city_options()
        except GmairError as err:
            _LOGGER.debug("city options failed: %s", err)
            errors["base"] = "cannot_connect"

        if not options:
            options = {DEFAULT_CITY_ID: DEFAULT_CITY_ID}

        current = self.config_entry.options.get(CONF_CITY_ID, DEFAULT_CITY_ID)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY_ID, default=current): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": value, "label": label}
                                for value, label in options.items()
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )
