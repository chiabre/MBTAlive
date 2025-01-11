from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback, EntityPlatform

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from mbtaclient import JourneysHandler, Journey

_LOGGER = logging.getLogger(__name__)

class MBTAJourneySensor(SensorEntity):
    """Representation of a MBTA Journey Sensor that tracks journey information"""
    
    def __init__(self, name, hass: HomeAssistant, journeys_handler: JourneysHandler):
        """Initialize the sensor."""
        self._name = name
        self._unique_id = f"mbtalive_{name.replace(' ', '_')}"  # Unique ID for the sensor
        self._hass = hass  # Store reference to Home Assistant object
        self._journeys_handler = journeys_handler  # Reference to the JourneysHandler
        self._journey: Journey = None  # Placeholder for the journey data
        self._attributes = {}  # Store additional attributes
        self._icon = "mdi:train-bus"  # Initial icon value

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor as a duration (in seconds) until departure."""
        if self._journey:
            departure_time = self._journey.get_stop_time_to('departure')
            if departure_time:
                _LOGGER.debug(f"Getting state for '{self._name}', departure in {departure_time} seconds.")
                return round((departure_time / 60),0)  # Return time to departure as the state (in minutes)
            else:
                _LOGGER.warning(f"No departure time found for '{self._name}'.")
        else:
            _LOGGER.warning(f"State requested for '{self._name}', but no journey data available.")
        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes for the sensor."""
        if self._journey:
            route_type = self._journey.get_route_type()
            if route_type in [0, 1, 2, 4]:
                line = self._journey.get_route_long_name()
            elif route_type == 3:
                line = self._journey.get_route_short_name()
            if route_type == 2:
                train_number = self._journey.get_trip_name()
            else:
                train_number = "NA"
            self._attributes = {
                "Line": line,
                "Type": self._journey.get_route_description(),
                "Color": "#"+self._journey.get_route_color(),
                "Train Number": train_number,
                "Direction": f"{self._journey.get_trip_direction()} to {self._journey.get_trip_destination()}",
                "Destination": self._journey.get_trip_headsign(),
                "Duration": str(timedelta(seconds=self._journey.get_trip_duration() or 0)),
                "Departure station": self._journey.get_stop_name('departure'),
                "Departure platform": self._journey.get_platform_name('departure'),
                "Departure time": self._journey.get_stop_time('departure'),
                "Departure delay": self._format_timedelta(seconds=self._journey.get_stop_delay('departure')),
                "Time to departure": str(timedelta(seconds=self._journey.get_stop_time_to('departure') or 0)),
                "Departure status": self._journey.get_stop_status('departure'),
                "Arrival station": self._journey.get_stop_name('arrival'),
                "Arrival platform": self._journey.get_platform_name('arrival'),
                "Arrival time": self._journey.get_stop_time('arrival'),
                "Arrival delay": self._format_timedelta(self._journey.get_stop_delay('arrival')),
                "Time to arrival": str(timedelta(seconds=self._journey.get_stop_time_to('arrival') or 0)),
                "Arrival status": self._journey.get_stop_status('arrival'),
            }            
            # Add alerts if any
            if self._journey.alerts:
                alerts = [
                    (f"({i+1}) ") + 
                    self._journey.get_alert_header(i) 
                    for i, _ in enumerate(self._journey.alerts) 
                ]
                self._attributes["alerts"] = alerts

        return self._attributes

    def _format_timedelta(self, seconds):
        """Format the timedelta to HH:MM:SS, including negative values."""
        if seconds is None:
            return "00:00:00"
        # Ensure the seconds value is an integer
        seconds = int(seconds)
        # Determine if the time is negative
        negative = seconds < 0
        if negative:
            seconds = abs(seconds)  # Make seconds positive for formatting
        # Calculate hours, minutes, and seconds
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        # Format as HH:MM:SS
        formatted_time = f"{'-' if negative else ''}{hours:02}:{minutes:02}:{seconds:02}"
        return formatted_time

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION  # Define the sensor as a duration type

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES  # Sensor's unit of measurement is minutes

    async def async_update(self):
        """Fetch the latest journey data."""
        try:
            _LOGGER.debug(f"Attempting to fetch journey data for '{self._name}'...")
            journeys: list[Journey] = await self._journeys_handler.update()
            if journeys:
                self._journey = journeys[0]
                _LOGGER.debug(f"Updated journey data for sensor '{self._name}': {self._journey}")          
            else:
                _LOGGER.warning(f"No journeys returned for '{self._name}'.")
        except Exception as e:
            _LOGGER.error(f"Error updating journey data for sensor '{self._name}': {e}")
            self._journey: Journey = None  # Clear the journey data in case of an error

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up sensors.")

    depart_from = entry.data.get("depart_from")
    arrive_at = entry.data.get("arrive_at")
    api_key = entry.data.get("api_key")
    title = entry.title  # Get the title of the config entry

    _LOGGER.debug(f"Extracted config entry data - Depart from: {depart_from}, Arrive at: {arrive_at}, API Key: {api_key}")

    try:
        journeys_handler = JourneysHandler(
            depart_from_name=depart_from,
            arrive_at_name=arrive_at,
            max_journeys=1,
            api_key=api_key,
            session=None,
            logger=_LOGGER
        )
        await journeys_handler.async_init()  # Initialize the handler
        _LOGGER.debug("JourneysHandler initialized successfully.")
               
        # Create a unique sensor name based on the entry title
        sensor_name = f"MBTA: {title}"
        
        # Create the sensor entity and immediately update its state
        sensor = MBTAJourneySensor(name=sensor_name, hass=hass, journeys_handler=journeys_handler)
        await sensor.async_update()  # Fetch and update journey data right away
        
        # Add the sensor entity to Home Assistant
        async_add_entities([sensor])

    except Exception as e:
        _LOGGER.error(f"Error initializing MBTA journeys handler: {e}")
        return False  # Indicate setup failure in case of error
