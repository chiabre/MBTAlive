import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import callback

from mbtaclient.handlers.base_handler import MBTAStopError
from mbtaclient.handlers.trips_handler import TripsHandler
from mbtaclient.handlers.trains_handler import TrainsHandler, MBTATripError
from mbtaclient.client.mbta_client import MBTAClient, MBTAAuthenticationError
from mbtaclient.client.mbta_cache_manager import MBTACacheManager
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_user_schema(default_api_key: str = "") -> vol.Schema:
    return vol.Schema({
        vol.Required("depart_from", default=""): str,
        vol.Required("arrive_at", default=""): str,
        vol.Required("api_key", default=default_api_key): vol.All(str, vol.Length(min=32, max=32)),
        vol.Optional("max_trips", default=2): int,
        vol.Optional("train", default=""): vol.Optional(str, vol.Length(min=3, max=3))
    })


class MBTAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the MBTA integration."""
    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        errors = {}
        default_api_key = ""
        if DOMAIN in self.hass.data and (client := self.hass.data[DOMAIN].get("mbta_client")):
            default_api_key = client._api_key

        if user_input is not None:
            depart_from = user_input.get("depart_from")
            arrive_at = user_input.get("arrive_at")
            api_key = user_input.get("api_key", "").strip()
            train = user_input.get("train", "")

            if not api_key:
                errors["api_key"] = "required"
            else:
                try:
                    if DOMAIN not in self.hass.data:
                        self.hass.data[DOMAIN] = {}

                    existing_client: MBTAClient = self.hass.data[DOMAIN].get("mbta_client")
                    if existing_client:
                        if existing_client._api_key != api_key:
                            _LOGGER.debug("Updating API key on existing MBTAClient")
                            existing_client._api_key = api_key
                        client = existing_client
                    else:
                        client = MBTAClient(api_key=api_key, cache_manager=MBTACacheManager())
                    
                    if train:
                        _LOGGER.debug("Validating via TrainsHandler for train %s", train)
                        await TrainsHandler.create(
                            departure_stop_name=depart_from,
                            mbta_client=client,
                            trip_name=train,
                            arrival_stop_name=arrive_at,
                            max_trips=1,
                        )
                    else:
                        _LOGGER.debug("Validating via TripsHandler")
                        await TripsHandler.create(
                            departure_stop_name=depart_from,
                            mbta_client=client,
                            arrival_stop_name=arrive_at,
                            max_trips=1,
                        )
                    self.hass.data[DOMAIN]["mbta_client"] = client

                except MBTAAuthenticationError:
                    errors["api_key"] = "api_key_invalid"
                    _LOGGER.debug("Invalid API key provided.")
                except MBTAStopError as e:
                    error_message = str(e).lower()
                    if "departure" in error_message:
                        errors["depart_from"] = "stop_not_found_depart_from"
                    elif "arrival" in error_message:
                        errors["arrive_at"] = "stop_not_found_arrive_at"
                    else:
                        errors["base"] = "stop_not_found"
                    _LOGGER.debug("Stop error: %s", e)
                except MBTATripError:
                    errors["train"] = "train_not_found"
                    _LOGGER.debug("Train error")
                except ValueError as e:
                    errors["base"] = "invalid_input"
                    _LOGGER.debug("Invalid input: %s", e)
                except Exception as e:
                    errors["base"] = "api_key_error"
                    _LOGGER.debug("Unexpected error: %s", e)

            if not errors:
                if train:
                    title = f"[{train}] {depart_from} → {arrive_at}"
                else:
                    title = f"{depart_from} → {arrive_at}"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=get_user_schema(default_api_key),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return MBTAOptionsFlowHandler(config_entry)


class MBTAOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options flow for MBTA integration."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow handler."""
        self._entry = entry

    @property
    def config_entry(self) -> config_entries.ConfigEntry:
        """Return the config entry."""
        return self._entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle the options step."""
        if user_input is not None:
            # Update only the max_trips option.
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, **user_input}
            )
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data
        OPTIONS_SCHEMA = vol.Schema({
            vol.Optional(
                "max_trips",
                default=current_data.get("max_trips", 2)
            ): vol.All(int, vol.Range(min=1))
        })

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
