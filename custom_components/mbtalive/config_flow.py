import logging
from typing import Any, Dict, Optional
import voluptuous as vol
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
    """
    Generate and return the schema for the configuration form.

    The 'api_key' field is pre-populated with default_api_key if available.
    """
    _LOGGER.debug("Generating user schema with default API key: %s", default_api_key)
    return vol.Schema(
        {
            vol.Required("depart_from", default=""): str,
            vol.Required("arrive_at", default=""): str,
            # Prepopulate API key if one exists.
            vol.Required("api_key", default=default_api_key): vol.All(str, vol.Length(min=32, max=32)),
            vol.Optional("max_trips", default=2): int,
            vol.Optional("train", default=""): vol.Optional(str, vol.Length(min=3, max=3)),
        }
    )

class MBTAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the MBTA integration."""
    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process the initial configuration step.

        This method validates the API key and stop names, and checks whether an MBTAClient
        already exists in hass.data. If it does, its API key is updated if necessary.
        """
        errors = {}

        # Try to prepopulate the API key from an existing client (if any)
        default_api_key = ""
        if DOMAIN in self.hass.data and (client := self.hass.data[DOMAIN].get("mbta_client")):
            default_api_key = client._api_key
            _LOGGER.debug("Using existing API key for form default: %s", default_api_key)

        if user_input is not None:
            depart_from = user_input.get("depart_from")
            arrive_at = user_input.get("arrive_at")
            # Remove extra whitespace from API key
            api_key = user_input.get("api_key", "").strip()
            train = user_input.get("train", "")

            if not api_key:
                _LOGGER.debug("No API key provided by the user.")
                errors["api_key"] = "required"
            else:
                try:
                    # Ensure our integration data container exists.
                    if DOMAIN not in self.hass.data:
                        self.hass.data[DOMAIN] = {}

                    # Check if an MBTAClient already exists
                    existing_client: MBTAClient = self.hass.data[DOMAIN].get("mbta_client")
                    if existing_client:
                        if existing_client._api_key != api_key:
                            _LOGGER.debug("Updating existing MBTAClient API key from %s to %s", existing_client._api_key, api_key)
                            existing_client._api_key = api_key
                        client = existing_client
                    else:
                        _LOGGER.debug("Creating new MBTAClient instance in config flow with API key: %s", api_key)
                        # Here, you can pass a cache manager if desired.
                        client = MBTAClient(api_key=api_key, cache_manager=MBTACacheManager(requests_per_stats_report=1000,logger=_LOGGER))
                        #self.hass.data[DOMAIN]["mbta_client"] = client

                    if train:
                        _LOGGER.debug("Validating API key via TrainsHandler for train %s between stops: %s -> %s", train, depart_from, arrive_at)
                        await TrainsHandler.create(
                            departure_stop_name=depart_from,
                            mbta_client=client,
                            trip_name=train,
                            arrival_stop_name=arrive_at,
                            max_trips=1,
                        )
                    else:
                        # Validate the API key and stops by attempting to create a TripsHandler.
                        _LOGGER.debug("Validating API key via TripsHandler for stops: %s -> %s", depart_from, arrive_at)
                        await TripsHandler.create(
                            departure_stop_name=depart_from,
                            mbta_client=client,
                            arrival_stop_name=arrive_at,
                            max_trips=1,
                        )
                    _LOGGER.debug("API key validation successful.")
                    self.hass.data[DOMAIN]["mbta_client"] = client

                except MBTAAuthenticationError:
                    errors["api_key"] = "api_key_invalid"
                    _LOGGER.debug("Authentication error: Invalid API key (HTTP 403).")

                except MBTAStopError as e:
                    error_message = str(e).lower()
                    if "departure" in error_message:
                        errors["depart_from"] = "stop_not_found_depart_from"
                    elif "arrival" in error_message:
                        errors["arrive_at"] = "stop_not_found_arrive_at"
                    else:
                        errors["base"] = "stop_not_found"  # Generic stop error
                    _LOGGER.debug("Stop validation error: %s", e)
            
                except MBTATripError:
                    errors["train"] = "train_not_found"
                    _LOGGER.debug("Train validation erro")

                except ValueError as e:
                    _LOGGER.debug("Invalid input detected: %s", e)
                    errors["base"] = "invalid_input"

                except Exception as e:
                    _LOGGER.debug("Unexpected error during API key or stop validation: %s", e)
                    errors["base"] = "api_key_error"

            if not errors:
                title = f"{depart_from} - {arrive_at}"
                _LOGGER.debug("Creating config entry with title: %s", title)
                return self.async_create_entry(title=title, data=user_input)

        _LOGGER.debug("Showing form with default API key: %s", default_api_key)
        return self.async_show_form(
            step_id="user", data_schema=get_user_schema(default_api_key), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return an instance of the options flow handler for updating settings."""
        return MBTAOptionsFlowHandler(config_entry)

class MBTAOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for the MBTA integration to allow updating settings."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow with the current configuration entry."""
        self.config_entry = config_entry
        _LOGGER.debug("Initialized options flow handler for config entry: %s", config_entry.entry_id)

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process the initial step in the options flow.

        Pre-populates the form with the existing configuration data.
        """
        if user_input is not None:
            _LOGGER.debug("User input received in options flow: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        current_data = self.config_entry.data
        _LOGGER.debug("Prepopulating options flow with current data: %s", current_data)
        data_schema = vol.Schema(
            {
                vol.Required("depart_from", default=current_data.get("depart_from", "")):
                    str,
                vol.Required("arrive_at", default=current_data.get("arrive_at", "")):
                   str,
                vol.Required("api_key", default=current_data.get("api_key", "")):
                    vol.All(str, vol.Length(min=32, max=32)),
                vol.Optional("max_trips", default=current_data.get("max_trips", 2)):
                    int,
                vol.Optional("train",  default=current_data.get("train", "")):
                    vol.Optional(str, vol.Length(min=3, max=3)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
