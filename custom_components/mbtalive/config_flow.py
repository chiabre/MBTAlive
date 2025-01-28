import logging
from typing import Dict

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
)

from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_MODE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_UNIQUE_ID,
)
from homeassistant.core import callback

from mbtaclient.handlers.trips_handler import TripsHandler
from mbtaclient.client.mbta_client  import MBTAClient

 
from .const import (
    DEFAULT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("depart_from"): vol.All(str, vol.Length(min=3)),
        vol.Required("arrive_at"): vol.All(str, vol.Length(min=3)),
        vol.Optional("api_key"): str,
    }
)

class MBTAConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MBTA."""
    VERSION = 1
    _name: str = DEFAULT_NAME

    async def async_step_user(self, user_input=None):
        """Handle the user-initiated configuration step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            depart_from = user_input.get("depart_from")
            arrive_at = user_input.get("arrive_at")
            api_key = user_input.get("api_key")

            _LOGGER.debug(f"User input received: {user_input}")

            try:
                
                mbta_client = MBTAClient(api_key=api_key)
                await TripsHandler.create(departure_stop_name=depart_from, mbta_client=mbta_client,arrival_stop_name=arrive_at, max_trips=1)
     
                # If no exceptions are raised, the connection is successful
                _LOGGER.debug("Connection to MBTA API successful.")

            except ValueError as e:
                _LOGGER.error(f"Invalid input: {e}")
                errors["base"] = "invalid_input"
            except Exception as e:
                _LOGGER.error(f"Unexpected error: {e}")
                errors["base"] = (f"{e}")

            if not errors:
                name = f"{depart_from} to {arrive_at}"
                _LOGGER.debug(f"Creating entry with name: {name}")
                return self.async_create_entry(title=name, data=user_input)

        _LOGGER.debug("Showing form with errors (if any)")
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)