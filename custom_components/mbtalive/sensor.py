from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt

from mbtaclient import JourneysHandler, Journey

_LOGGER = logging.getLogger(__name__)


class MBTAJourneyCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching journey data for sensors."""

    def __init__(self, hass, journeys_handler: JourneysHandler):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MBTA Journey Data",
            update_interval=timedelta(seconds=30),
        )
        self.journeys_handler: JourneysHandler = journeys_handler

    async def _async_update_data(self):
        """Fetch data from the MBTA API."""
        try:
            journeys: list[Journey] = await self.journeys_handler.update()
            if not journeys:
                raise UpdateFailed("No journeys returned from the MBTA API.")
            return journeys
        except Exception as err:
            raise UpdateFailed(f"Error fetching journey data: {err}")


class MBTABaseJourneySensor(SensorEntity):
    """Base class for MBTA journey sensors."""

    def __init__(self, name, coordinator, sensor_type, config_entry_id):
        """Initialize the base sensor."""
        self._coordinator = coordinator
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{config_entry_id}-{sensor_type}"  # Unique ID for the entity
        self._attr_device_info = {
            "identifiers": {(config_entry_id,)},
            "name": name,
            "manufacturer": "chiabre",
            "model": "MBTA Live Journey Sensor",
        }
        self._attr_config_entry_id = config_entry_id  # Link entity to config entry

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._sensor_type}"

    @property
    def available(self):
        """Return if the sensor is available."""
        return self._coordinator.last_update_success

    async def async_update(self):
        """Fetch the latest data from the coordinator."""
        await self._coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            journey = self._coordinator.data[0]  # Assuming only one journey
            return {
                "Type": journey.get_route_description(),
                "Color": "#"+journey.get_route_color(),
            }
        return None


class MBTADepartureTimeToSensor(MBTABaseJourneySensor):
    """Sensor for departure time."""
    
    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data and self._coordinator.data[0].get_stop_time_to("departure"):
            journey: Journey = self._coordinator.data[0]  # Assuming only one journey
            return journey.get_stop_time_to("departure") / 60
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES
    
class MBTADepartureTimeSensor(MBTABaseJourneySensor):
    """Sensor for departure time."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data and self._coordinator.data[0].get_stop_time("departure"):
            journey: Journey = self._coordinator.data[0]  # Assuming only one journey
            return journey.get_stop_time("departure").replace(tzinfo=None)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        # No unit is necessary for the platform name, so None.
        return None

class MBTADepartureDelaySensor(MBTABaseJourneySensor):
    """Sensor for departure time."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data and self._coordinator.data[0].get_stop_time("departure"):
            journey: Journey = self._coordinator.data[0]  # Assuming only one journey
            departure_delay = journey.get_stop_delay('departure')
            if departure_delay is not None:
                return departure_delay / 60
            else:
                return 0  # Default value when there's no delay
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES
    
class MBTADepartureStatusSensor(MBTABaseJourneySensor):
    """Sensor for departure time."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data and self._coordinator.data[0].get_stop_status("departure"):
            journey: Journey = self._coordinator.data[0]  # Assuming only one journey
            return journey.get_stop_status('departure')
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        return None 
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        # No unit is necessary for the platform name, so None.
        return None

class MBTADeparturePlatformSensor(MBTABaseJourneySensor):
    """Sensor for departure platfomr."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data and self._coordinator.data[0].get_platform_name("departure"):
            journey: Journey = self._coordinator.data[0]  # Assuming only one journey
            return journey.get_platform_name("departure")
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        return None 
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        # No unit is necessary for the platform name, so None.
        return None
    
class MBTADestinationSensor(MBTABaseJourneySensor):
    """Sensor for journey direction."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            journey: Journey = self._coordinator.data[0]  # Assuming only one journey
            return journey.get_trip_headsign()
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up sensors.")

    depart_from = entry.data.get("depart_from")
    arrive_at = entry.data.get("arrive_at")
    api_key = entry.data.get("api_key")
    title = entry.title
    config_entry_id = entry.entry_id

    try:
        journeys_handler = JourneysHandler(
            depart_from_name=depart_from,
            arrive_at_name=arrive_at,
            max_journeys=1,
            api_key=api_key,
            session=None,
            logger=_LOGGER,
        )
        await journeys_handler.async_init()

        coordinator = MBTAJourneyCoordinator(hass, journeys_handler)
        await coordinator.async_config_entry_first_refresh()
        #coordinator.data[0]

        sensors = [
            MBTADepartureTimeToSensor(title, coordinator, "Next departure", config_entry_id),
            MBTADepartureTimeSensor(title, coordinator, "Departure time", config_entry_id),
            MBTADepartureDelaySensor(title, coordinator, "Delay", config_entry_id),
            MBTADepartureStatusSensor(title, coordinator, "Status", config_entry_id),
            MBTADeparturePlatformSensor(title, coordinator, "Platfomr", config_entry_id),
            MBTADestinationSensor(title, coordinator, "Direction", config_entry_id),
        ]
        async_add_entities(sensors)

    except Exception as e:
        _LOGGER.error(f"Error initializing MBTA journeys handler: {e}")
        return False
