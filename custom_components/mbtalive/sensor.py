from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity

from homeassistant.helpers.entity import generate_entity_id

from mbtaclient.handlers.trips_handler import TripsHandler
from mbtaclient.client.mbta_client  import MBTAClient
from mbtaclient.client.mbta_cache_manager  import MBTACacheManager
from mbtaclient.trip import Trip
from mbtaclient.stop import StopType

_LOGGER = logging.getLogger(__name__)

class MBTATripCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching trips data for sensors."""

    UPDATE_INTERVAL = timedelta(seconds=20)
    
    def __init__(self, hass, trips_handler: TripsHandler):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MBTA Trip Data",
            update_interval=self.UPDATE_INTERVAL,
        )
        self.trips_handler: TripsHandler = trips_handler

    async def _async_update_data(self):
        """Fetch data from the MBTA API while preserving the last known good data."""
        try:
            _LOGGER.debug("Fetching trips data from MBTA API")
            trips: list[Trip] = await self.trips_handler.update()
            if not trips:
                raise UpdateFailed("No trips returned from the MBTA API.")

            self._last_successful_data = trips  # Update the last known data
            return trips  # Return new data

        except UpdateFailed as e:
            _LOGGER.error(f"Update failed: {e}")
            if self._last_successful_data:
                _LOGGER.warning("Using last known good data instead.")
                return self._last_successful_data  # Keep old data instead of making sensors unavailable
            raise

        except Exception as err:
            _LOGGER.error(f"Error fetching trips data: {err}")
            if self._last_successful_data:
                _LOGGER.warning("Using last known good data instead.")
                return self._last_successful_data
            raise UpdateFailed(f"Error fetching trips data: {err}")

class MBTABaseTripSensor(CoordinatorEntity, SensorEntity):
    """Base class for MBTA trip sensors."""

    def __init__(
        self,
        config_entry_name,
        config_entry_id,
        coordinator: MBTATripCoordinator,
        sensor_name,
        icon):
        """Initialize the base sensor."""
        super().__init__(coordinator)  # Ensures entity is linked to the coordinator
        
        if isinstance(self,MBTATripSensor) or isinstance(self,MBTANextTripSensor):
            entity_id = f"{sensor_name}"
        else:
            entity_id = f"({config_entry_name}_{sensor_name})"

        self._attr_config_entry_id = config_entry_id  # Link entity to config entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{config_entry_id}-{sensor_name}"  # Unique ID for the entity
        self._sensor_name = sensor_name
        self.entity_id = generate_entity_id(
            "sensor.{}",
            entity_id,
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

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_countdown:
                return trip.departure_countdown
        return "unavailable"  # If no data ever existed, return unavailable

    async def async_update(self):
        """Ensure sensor updates when the coordinator updates."""
        self.async_write_ha_state()  # Ensures UI update when coordinator updates

#TRIP


class MBTATripSensor(MBTABaseTripSensor):
    """Sensor for the trip."""

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_countdown:
                return trip.departure_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.departure_stop_name:
                attributes["from"]  = trip.departure_stop_name  
            if trip.arrival_stop_name:
                attributes["to"]  = trip.arrival_stop_name  
            if trip.headsign:
                attributes["headsign"]  = trip.headsign               
            if trip.name:
                attributes["train"]  = trip.name
            if trip.duration:
                attributes["duration"]  =  f"{int(round(trip.duration / 60,0))}m"
            if trip.departure_platform:
                attributes["platform"]  = trip.departure_platform
            if trip.departure_time:
                 attributes["time"]  = trip.departure_time
            if trip.departure_delay:
                 attributes["delay"]  = f"{int(round(trip.departure_delay / 60,0))}m"
            if trip.route_name:
                attributes["line"]  = trip.route_name
            if trip.route_description:
                attributes["type"]  = trip.route_description
            if trip.route_color:
                attributes["color"] = trip.route_color
            attributes["alerts"] = []
            if trip.alerts:
                attributes["alerts"] = " # ".join(trip.alerts)
            next = []
            for item in data[1:]:
                if item.departure_countdown:
                    next.append(item.departure_countdown)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        return None

class MBTANextTripSensor(MBTABaseTripSensor):
    """Sensor for the trip."""

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[1]
            if trip.departure_countdown:
                return trip.departure_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[1]
            attributes = {}
            if trip.departure_stop_name:
                attributes["from"]  = trip.departure_stop_name  
            if trip.arrival_stop_name:
                attributes["to"]  = trip.arrival_stop_name  
            if trip.headsign:
                attributes["headsign"]  = trip.headsign               
            if trip.name:
                attributes["train"]  = trip.name
            if trip.duration:
                attributes["duration"]  =  f"{int(round(trip.duration / 60,0))}m"
            if trip.departure_platform:
                attributes["platform"]  = trip.departure_platform
            if trip.departure_time:
                 attributes["time"]  = trip.departure_time
            if trip.departure_delay:
                 attributes["delay"]  = f"{int(round(trip.departure_delay / 60,0))}m"
            if trip.route_name:
                attributes["line"]  = trip.route_name
            if trip.route_description:
                attributes["type"]  = trip.route_description
            if trip.route_color:
                attributes["color"] = trip.route_color
            attributes["alerts"] = []    
            if trip.alerts:
                attributes["alerts"] = " # ".join(trip.alerts)
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTATrainSensor(MBTABaseTripSensor):
    """Sensor for trip name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.name:
                return trip.name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.name:
                    next.append(item.name)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTAHeadsignSensor(MBTABaseTripSensor):
    """Sensor for trip headsign."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.headsign:
                return trip.headsign
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            attributes = {}
            trip: Trip = data[0]
            if trip.name:
                attributes["name"]  = trip.name
            if trip.duration:
                attributes["duration"]  = f"{int(round(trip.duration/60,0))} min"
            if trip.destination:
                attributes["destination"]  = trip.destination
            if trip.direction:
                attributes["direction"]  = trip.direction
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.headsign:
                        next.append(item.headsign)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None

class MBTADestinationSensor(MBTABaseTripSensor):
    """Sensor for trip destination."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.destination:
                return trip.destination
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.destination:
                    next.append(item.destination)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADirectionSensor(MBTABaseTripSensor):
    """Sensor for trip direction."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.direction:
                return trip.direction
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.direction:
                    next.append(item.direction)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADurationSensor(MBTABaseTripSensor):
    """Sensor for departure time."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.duration:
                return round(trip.duration / 60,0)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.duration:
                    next.append(f"{round(item.duration / 60,0)}m")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
#ROUTE
class MBTARouteNameSensor(MBTABaseTripSensor):
    """Sensor for trip route name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.route_name:
                return trip.route_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.route_description:
                attributes["type"] = trip.route_description
            if trip.route_color:
                attributes["color"] = trip.route_color
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.route_name:
                        next.append(item.route_name)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None

class MBTARouteTypeSensor(MBTABaseTripSensor):
    """Sensor for route type."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.route_description:
                return trip.route_description
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.route_description:
                    next.append(item.route_description)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
      
class MBTARouteColorSensor(MBTABaseTripSensor):
    """Sensor for route type."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.route_color:
                return trip.route_color
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.route_color:
                    next.append(item.route_color)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes  

#VEHICLE
class MBTAVehicleStatusSensor(MBTABaseTripSensor):
    """Sensor for vehicle status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.vehicle_status:
                return trip.vehicle_status
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.vehicle_speed:
                attributes["speed"]  = trip.vehicle_speed
            if trip.vehicle_longitude:
                attributes["longitude"]  = trip.vehicle_longitude                
            if trip.vehicle_longitude:
                attributes["latitude"]  = trip.vehicle_latitude  
            if trip.vehicle_occupancy:
                attributes["occupancy"]  = trip.vehicle_occupancy                                  
            if trip.vehicle_updated_at:
                attributes["updated at"]  = trip.vehicle_updated_at           
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.vehicle_status:
                        next.append(item.vehicle_status)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None

class MBTAVehicleSpeedSensor(MBTABaseTripSensor):
    """Sensor for vehicle speed."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip._mbta_vehicle:
                if trip.vehicle_speed:
                    return trip.vehicle_speed
                return 0
        return "unavailable"

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return BinarySensorDeviceClass.UPDATE

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "mph"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.vehicle_updated_at:
                attributes["updated_at"]  = trip.vehicle_updated_at
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.vehicle_speed:
                        next.append(item.vehicle_speed)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None
    
class MBTAVehicleLonSensor(MBTABaseTripSensor):
    """Sensor for vehicle longitude."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.vehicle_longitude:
                return trip.vehicle_longitude
        return "unavailable"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "°"  # Degrees symbol for geographic coordinates

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.vehicle_updated_at:
                attributes["updated_at"]  = trip.vehicle_updated_at
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.vehicle_longitude:
                        next.append(item.vehicle_longitude)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes

        return None

class MBTAVehicleLatSensor(MBTABaseTripSensor):
    """Sensor for vehicle longlatitude."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.vehicle_latitude:
                return trip.vehicle_latitude
        return "unavailable"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "°"  # Degrees symbol for geographic coordinates
        
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.vehicle_updated_at:
                 attributes["updated_at"]  = trip.vehicle_updated_at
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.vehicle_latitude:
                        next.append(item.vehicle_latitude)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        return None

class MBTAVehicleLiveData(MBTABaseTripSensor):
    """Sensor for vehicle last update."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            return trip.is_vehicle_data_fresh
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.is_vehicle_data_fresh:
                    next.append(item.is_vehicle_data_fresh)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
#DEPARTURE STOP
class MBTADepartureNameSensor(MBTABaseTripSensor):
    """Sensor for departure stop name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_stop_name:
                return trip.departure_stop_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.departure_platform:
                attributes["platform"]  = trip.departure_platform
            if trip.departure_countdown:
                attributes["countdown"]  = trip.departure_countdown
            return attributes  # Return the dictionary of attributes
        return None
    
class MBTADeparturePlatformSensor(MBTABaseTripSensor):
    """Sensor for departure platform name.."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_platform:
                return trip.departure_platform
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.departure_platform:
                    next.append(item.departure_platform)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADepartureTimeSensor(MBTABaseTripSensor):
    """Sensor for departure time."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_time:
                return trip.departure_time
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.departure_delay:
                attributes["delay"]  = f"{int(round(trip.departure_delay / 60,0))}m"
            if trip.departure_time_to:
                attributes["time to"]  = f"{int(round(trip.departure_time_to / 60,0))}m"
            if trip.departure_countdown:
                attributes["countdown"]  = trip.departure_countdown
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.departure_time:
                        next.append(item.departure_time)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        return None

class MBTADepartureDelaySensor(MBTABaseTripSensor):
    """Sensor for departure delay."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_delay:
                return round(trip.departure_delay / 60,0)
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.departure_delay:
                    next.append(f"{int(round(item.departure_delay / 60,0))}m")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTADepartureTimeToSensor(MBTABaseTripSensor):
    """Sensor for departure time to."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_time_to:
                time_to = round(trip.departure_time_to / 60,0)
                if time_to >= 0:
                    return time_to
                elif time_to < 0:
                    return 0
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.departure_time_to:
                    next.append(f"{int(round(item.departure_time_to / 60,0))}m")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes

class MBTADepartureMBTACountdownSensor(MBTABaseTripSensor):
    """Sensor for departure status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_MBTA_countdown:
                return trip.departure_MBTA_countdown
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.departure_MBTA_countdown:
                    next.append(item.departure_MBTA_countdown)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes

class MBTADepartureCountdownSensor(MBTABaseTripSensor):
    """Sensor for departure countdown."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.departure_countdown:
                return trip.departure_countdown
        return "unavailable"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.departure_countdown:
                    next.append(item.departure_countdown)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
#ARRIVAL STOP
class MBTAArrivalNameSensor(MBTABaseTripSensor):
    """Sensor for arrival stop name."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.arrival_stop_name:
                return trip.arrival_stop_name
        return None

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            if trip.arrival_platform:
                 attributes["platform"]  = trip.arrival_platform
            if trip.arrival_countdown:
                attributes["countdown"] = trip.arrival_countdown
            return attributes  # Return the dictionary of attributes

        return None
    
class MBTAArrivalPlatformSensor(MBTABaseTripSensor):
    """Sensor for arrival platform name.."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.arrival_platform:
                return trip.arrival_platform
        return None
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.arrival_platform:
                    next.append(item.arrival_platform)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes

class MBTAArrivalTimeSensor(MBTABaseTripSensor):
    """Sensor for arrival time."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default
    
    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.arrival_time:
                return trip.arrival_time
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        # Use None or other device classes based on the data.
        SensorDeviceClass.TIMESTAMP 
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            attributes = {}
            trip: Trip = data[0]
            if trip.arrival_delay:
                attributes["delay"] = f"{int(round(trip.arrival_delay / 60,0))}m"
            if trip.arrival_time_to:
                attributes["time to"] = f"{int(round(trip.arrival_time_to / 60,0))}m"
            if trip.arrival_countdown:
                attributes["countdown"]  = trip.arrival_countdown
            if len(self._coordinator.data) > 0:
                next = []
                for item in data[1:]:
                    if item.arrival_time:
                        next.append(item.arrival_time)
                if len(next) >0:
                    attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        return None

class MBTAArrivalDelaySensor(MBTABaseTripSensor):
    """Sensor for arrival delay."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.arrival_delay:
                return round(trip.arrival_delay / 60,0)
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

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.arrival_delay:
                    next.append(f"{int(round(item.arrival_delay / 60,0))}m")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTAArrivalTimeToSensor(MBTABaseTripSensor):
    """Sensor for arrival time to."""        

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.arrival_time_to:
                time_to = round(trip.arrival_time_to / 60,0)
                if time_to >= 0:
                    return time_to
                elif time_to < 0:
                    return 0
        return None

    @property
    def device_class(self):
        """Return the device class for the sensor."""
        return SensorDeviceClass.DURATION

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.arrival_time_to:
                    next.append(f"{int(round(item.arrival_time_to / 60,0))}m")
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
class MBTAArrivalMBTACountdownSensor(MBTABaseTripSensor):
    """Sensor for arrival status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.arrival_MBTA_countdown:
                return trip.arrival_MBTA_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.arrival_MBTA_countdown:
                    next.append(item.arrival_MBTA_countdown)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes

class MBTAArrivalCountdownSensor(MBTABaseTripSensor):
    """Sensor for arrival status."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.arrival_countdown:
                return trip.arrival_countdown
        return "unavailable"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data and len(data) > 0:
            attributes = {}
            next = []
            for item in data[1:]:
                if item.arrival_countdown:
                    next.append(item.arrival_countdown)
            if len(next) >0:
                attributes["next"] = next
            return attributes  # Return the dictionary of attributes
        
#ALERTS
class MBTAAlertsSensor(MBTABaseTripSensor):
    """Sensor for trip alerts."""

    _attr_entity_registry_enabled_default = False  # This keeps the sensor disabled by default

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            if trip.alerts:
                return len(trip.alerts)
        return 0

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement for the sensor."""
        return "alerts"  # Count of alerts

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or self.coordinator._last_successful_data  # Use last known good data
        if data:
            trip: Trip = data[0]
            attributes = {}
            # Add alerts
            if trip.alerts:
                attributes["alerts"] = " # ".join(trip.alerts)
            return attributes  # Return the dictionary of attributes
        return None

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up MBTA Trip sensors")

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

        trips_handler = await TripsHandler.create(departure_stop_name=depart_from, mbta_client=mbta_client,arrival_stop_name=arrive_at, sort_by=StopType.ARRIVAL, max_trips=2)
        # Create and refresh the coordinator
        coordinator = MBTATripCoordinator(hass, trips_handler)

        _LOGGER.debug("Refreshing coordinator")

        await coordinator.async_config_entry_first_refresh()

        # Get the first trip and determine the route icon
        trip: Trip = coordinator.data[0]
        route_type = trip._mbta_route.type
        icon = {
            0: "mdi:subway-variant",
            1: "mdi:subway-variant",
            2: "mdi:train",
            3: "mdi:bus",
            4: "mdi:ferry",
        }.get(route_type, "mdi:train")

        trip = f"{trip.departure_stop_name} - {trip.arrival_stop_name}"
        # Create sensors
        _LOGGER.debug("Creating sensors for trip data")
        sensors = [
            MBTATripSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name=trip,icon=icon),
            MBTANextTripSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name=f"{trip} (next)",icon=icon),
            MBTAHeadsignSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Headsign",icon="mdi:sign-direction"),
            MBTADestinationSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Destination",icon="mdi:sign-direction"),
            MBTADirectionSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Direction",icon="mdi:sign-direction"),
            MBTADurationSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Duration",icon="mdi:timelapse"),
            MBTARouteNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Line",icon=icon),
            MBTARouteTypeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Type",icon=icon),
            MBTARouteColorSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Color",icon=icon),
            MBTADepartureNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="From",icon="mdi:bus-stop-uncovered",),
            MBTADepartureTimeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Time",icon="mdi:clock-start"),
            MBTADepartureDelaySensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Delay",icon="mdi:clock-alert-outline"),
            MBTADepartureTimeToSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Time To Departure",icon="mdi:progress-clock"),
            MBTADepartureMBTACountdownSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure MBTA Countdown",icon="mdi:timer-marker-outline"),
            MBTADepartureCountdownSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Countdown",icon="mdi:timer-marker-outline"),
            MBTAArrivalNameSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="To",icon="mdi:bus-stop-uncovered"),
            MBTAArrivalTimeSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Time",icon="mdi:clock-end"),
            MBTAArrivalDelaySensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Delay",icon="mdi:clock-alert-outline"),
            MBTAArrivalTimeToSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Time To Arrival",icon="mdi:progress-clock"),
            MBTAArrivalMBTACountdownSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival MBTA Countdown",icon="mdi:timer-marker-outline"),
            MBTAArrivalCountdownSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Countdown",icon="mdi:timer-marker-outline"),
            MBTAAlertsSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Alerts",icon="mdi:alert-outline"),
        ]

        if route_type == 2:
            sensors.append( MBTATrainSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Train",icon=icon))

        if route_type != 3:
            sensors.append( MBTADeparturePlatformSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Departure Platform",icon="mdi:bus-stop-uncovered"))
            sensors.append(MBTAArrivalPlatformSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Arrival Platform",icon="mdi:bus-stop-uncovered"))
            sensors.append(MBTAVehicleStatusSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Status",icon="mdi:signal-variant"))
            sensors.append(MBTAVehicleSpeedSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Speed",icon="mdi:speedometer"))
            sensors.append(MBTAVehicleLonSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Longitude",icon="mdi:map-marker"))
            sensors.append(MBTAVehicleLatSensor(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Latitude",icon="mdi:map-marker"))
            sensors.append(MBTAVehicleLiveData(config_entry_name=name,config_entry_id=config_entry_id,coordinator=coordinator,sensor_name="Live Data",icon="mdi:signal-variant"))

        # Add the sensors to Home Assistant
        async_add_entities(sensors)
        _LOGGER.debug("Setting up MBTA Trip sensors completed successfully.")
        return True

    except Exception as e:
        _LOGGER.error(f"Error setting up MBTA Trip sensors: {e}")
        return False
