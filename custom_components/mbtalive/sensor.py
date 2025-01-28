from datetime import timedelta
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
from homeassistant.helpers.entity import generate_entity_id

from mbtaclient.handlers.trips_handler import TripsHandler
from mbtaclient.client.mbta_client  import MBTAClient
from mbtaclient.client.mbta_cache_manager  import MBTACacheManager
from mbtaclient.trip import Trip

_LOGGER = logging.getLogger(__name__)

class MBTAJourneyCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching journey data for sensors."""

    def __init__(self, hass, trips_handler: TripsHandler):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MBTA Trip Data",
            update_interval=timedelta(seconds=15),
        )
        self.trips_handler: TripsHandler = trips_handler

    async def _async_update_data(self):
        """Fetch data from the MBTA API."""
        try:
            _LOGGER.debug("Fetching journey data from MBTA API")
            trips: list[Trip] = await self.trips_handler.update()
            if not trips:
                raise UpdateFailed("No journeys returned from the MBTA API.")
            return trips[0]
        except UpdateFailed as e:
            _LOGGER.error(f"Update failed: {e}")
            raise  # Re-raise to propagate the error
        except Exception as err:
            _LOGGER.error(f"Error fetching journey data: {err}")
            raise UpdateFailed(f"Error fetching journey data: {err}")

class MBTABaseJourneySensor(SensorEntity):
    """Base class for MBTA journey sensors."""

    def __init__(
        self, 
        config_entry_name, 
        config_entry_id, 
        coordinator, 
        sensor_name,
        icon):
        """Initialize the base sensor."""

        self._attr_config_entry_id = config_entry_id  # Link entity to config entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{config_entry_id}-{sensor_name}"  # Unique ID for the entity
        self._sensor_name = sensor_name
        self.entity_id = generate_entity_id(
            "sensor.{}",
            f"({config_entry_name}_{sensor_name})",
            hass=self._coordinator.hass
        )
        self._attr_device_info = {
            "identifiers": {(config_entry_id,)},
            "name": config_entry_name,
            "model": "MBTA Live Trip Info",
        }
        self._attr_icon = icon 

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._sensor_name}"

    @property
    def available(self):
        """Return if the sensor is available."""
        return self._coordinator.last_update_success

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return self._attr_icon

    async def async_update(self):
        """Fetch the latest data from the coordinator."""
        await self._coordinator.async_request_refresh()

    # @property
    # def extra_state_attributes(self):
    #     """Return extra attributes."""
    #     if self._coordinator.data:
    #         trip: Trip = self._coordinator.data[0]  # Assuming only one journey
    #         alerts = "-"
    #         if trip.mbta_alerts:
    #             alerts = [
    #                 (f"({i+1}) ") + alert.short_header(i) 
    #                 for i, alert in enumerate(trip.mbta_alerts)
    #             ]
    #         return {
    #             "Line Color": "#"+trip.route_color,
    #             "Alerts": alerts if alerts != "-" else "No alerts"
    #         }
    #     return None

#TRIP
class MBTAHeadsignSensor(MBTABaseJourneySensor):
    """Sensor for trip headsign."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.headsign:
                return trip.headsign
        return None

class MBTANameSensor(MBTABaseJourneySensor):
    """Sensor for trip name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.name:
                return trip.name
        return None

class MBTADestinationSensor(MBTABaseJourneySensor):
    """Sensor for trip destination."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.direction_destination:
                return trip.direction_destination
        return None

class MBTADirectionSensor(MBTABaseJourneySensor):
    """Sensor for trip direction."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.direction_name:
                return trip.direction_name
        return None       

class MBTADurationSensor(MBTABaseJourneySensor):
    """Sensor for departure time."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.duration:
                return round(trip.duration.seconds / 60,0)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

#ROUTE
class MBTARouteNameSensor(MBTABaseJourneySensor):
    """Sensor for trip route name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.route_name:
                return trip.route_name
        return None

class MBTARouteTypeSensor(MBTABaseJourneySensor):
    """Sensor for route type."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.route_description:
                return trip.route_description
        return None

#VEHICLE
class MBTAVehicleLonSensor(MBTABaseJourneySensor):
    """Sensor for vehicle longitude."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.vehicle_longitude:
                return trip.vehicle_longitude
        return None 
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "°"  # Degrees symbol for geographic coordinates

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            attributes = {}

            if trip.vehicle_updated_at:
                attributes["updated_at"]  = trip.vehicle_updated_at.replace(tzinfo=None)

            return attributes  # Return the dictionary of attributes

        return None

class MBTAVehicleLatSensor(MBTABaseJourneySensor):
    """Sensor for vehicle longlatitude."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.vehicle_latitude:
                return trip.vehicle_latitude
        return None 

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "°"  # Degrees symbol for geographic coordinates

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            attributes = {}
    
            if trip.vehicle_updated_at:
                 attributes["updated_at"]  = trip.vehicle_updated_at.replace(tzinfo=None)
   
            return attributes  # Return the dictionary of attributes
 
        return None

class MBTAVehicleLastUpdateSensor(MBTABaseJourneySensor):
    """Sensor for vehicle last update."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.vehicle_updated_at:
                return trip.vehicle_updated_at.replace(tzinfo=None)
        return None

#DEPARTURE STOP
class MBTADepartureNameSensor(MBTABaseJourneySensor):
    """Sensor for departure stop name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.departure_stop_name:
                return trip.departure_stop_name
        return None

class MBTADeparturePlatformSensor(MBTABaseJourneySensor):
    """Sensor for departure platform name.."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.departure_platform_name:
                return trip.departure_platform_name
        return None

class MBTADepartureTimeSensor(MBTABaseJourneySensor):
    """Sensor for departure time."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.departure_time:
                return trip.departure_time.replace(tzinfo=None)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 

class MBTADepartureDelaySensor(MBTABaseJourneySensor):
    """Sensor for departure delay."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.departure_deltatime:
                return round(trip.departure_deltatime.total_seconds() / 60,0)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

class MBTADepartureTimeToSensor(MBTABaseJourneySensor):
    """Sensor for departure time to."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.departure_time_to:
                return round(trip.departure_time_to.total_seconds() / 60,0)
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
    """Sensor for departure status."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.departure_time_to:
                return trip.departure_status
        return None

#ARRIVAL STOO
class MBTAArrivalNameSensor(MBTABaseJourneySensor):
    """Sensor for arrival stop name."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.arrival_stop_name:
                return trip.arrival_stop_name
        return None

class MBTAArrivalPlatformSensor(MBTABaseJourneySensor):
    """Sensor for arrival platform name.."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.arrival_platform_name:
                return trip.arrival_platform_name
        return None

class MBTAArrivalTimeSensor(MBTABaseJourneySensor):
    """Sensor for arrival time."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.arrival_time:
                return trip.arrival_time.replace(tzinfo=None)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 

class MBTAArrivalDelaySensor(MBTABaseJourneySensor):
    """Sensor for arrival delay."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.arrival_deltatime:
                return round(trip.arrival_deltatime.total_seconds() / 60,0)
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

class MBTAArrivalTimeToSensor(MBTABaseJourneySensor):
    """Sensor for arrival time to."""        

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.arrival_time_to:
                return round(trip.arrival_time_to.total_seconds() / 60,0)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

class MBTAArrivalStatusSensor(MBTABaseJourneySensor):
    """Sensor for arrival status."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.arrival_status:
                return trip.arrival_status
        return None

#ALERTS

class MBTAAlertsSensor(MBTABaseJourneySensor):
    """Sensor for trip alerts."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            if trip.mbta_alerts:
                return len(trip.mbta_alerts)
        return 0

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "alerts"  # Count of alerts

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if self._coordinator.data:
            trip: Trip = self._coordinator.data
            attributes = {}
            _LOGGER.debug(attributes)
            # Add alerts
            alerts = "-"
            if trip.mbta_alerts:
                alerts = ", ".join(mbta_alert.short_header for mbta_alert in trip.mbta_alerts)
                _LOGGER.debug(alerts)
            attributes["alerts"] = alerts
            _LOGGER.debug(attributes)

            return attributes  # Return the dictionary of attributes
        return None

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up MBTA journey sensors")

    # Extract configuration data
    depart_from = entry.data.get("depart_from")
    arrive_at = entry.data.get("arrive_at")
    api_key = entry.data.get("api_key")
    name = entry.title
    config_entry_id = entry.entry_id

    try:
        _LOGGER.debug(f"Initializing MBTAClient with API key {api_key}")

        mbta_client = MBTAClient(api_key=api_key,cache_manager=MBTACacheManager())
        
        _LOGGER.debug(f"Creating TripsHandler for departure from {depart_from} to {arrive_at}")

        trips_handler = await TripsHandler.create(departure_stop_name=depart_from, mbta_client=mbta_client,arrival_stop_name=arrive_at, max_trips=1)

        # Create and refresh the coordinator
        coordinator = MBTAJourneyCoordinator(hass, trips_handler)

        _LOGGER.debug("Refreshing coordinator")

        await coordinator.async_config_entry_first_refresh()

        # Get the first trip and determine the route icon
        trip: Trip = coordinator.data
        route_type = trip.route_type
        icon = {
            0: "mdi:subway-variant",
            1: "mdi:subway-variant",
            2: "mdi:train",
            3: "mdi:bus",
            4: "mdi:ferry",
        }.get(route_type, "mdi:train")

        # Create sensors
        _LOGGER.debug("Creating sensors for trip data")
        sensors = [
            MBTAHeadsignSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Headsign",icon="mdi:sign-direction"),
            MBTADestinationSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Destination",icon="mdi:sign-direction"),
            MBTADirectionSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Direction",icon="mdi:sign-direction"),
            MBTADurationSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Duration",icon="mdi:timelapse"),         
            MBTARouteNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Line",icon=icon),
            MBTARouteTypeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Type",icon=icon),
            MBTAVehicleLonSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Vehicle Longitude",icon="mdi:map-marker"),
            MBTAVehicleLatSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Vehicle Latitude",icon="mdi:map-marker"),
            MBTAVehicleLastUpdateSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Vehicle Last Update",icon="mdi:update"),
            MBTADepartureNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure",icon="mdi:bus-stop-uncovered",),
            MBTADeparturePlatformSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Platform",icon="mdi:bus-stop-uncovered"),
            MBTADepartureTimeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Time",icon="mdi:clock-start"),
            MBTADepartureDelaySensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Delay",icon="mdi:clock-alert-outline"),
            MBTADepartureTimeToSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Time To Departure",icon="mdi:progress-clock"),
            MBTADepartureStatusSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Status",icon="mdi:timetable"),
            MBTAArrivalNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival",icon="mdi:bus-stop-uncovered"),
            MBTAArrivalPlatformSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Platform",icon="mdi:bus-stop-uncovered"),
            MBTAArrivalTimeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Time",icon="mdi:clock-end"),
            MBTAArrivalDelaySensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Delay",icon="mdi:clock-alert-outline"),
            MBTAArrivalTimeToSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Time To Arrival",icon="mdi:progress-clock"),
            MBTAArrivalStatusSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Status",icon="mdi:timetable"),
            MBTAAlertsSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Alerts",icon="mdi:alert-outline"),
        ]

        if route_type == 2: 
            mbta_name_sensor = MBTANameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Train",icon=icon)
            sensors.append(mbta_name_sensor)

        # Add the sensors to Home Assistant
        async_add_entities(sensors)
        _LOGGER.debug("Setting up MBTA journey sensors completed successfully.")
        return True

    except Exception as e:
        _LOGGER.error(f"Error setting up MBTA journey sensors: {e}")
        return False
