from datetime import datetime, timedelta
import logging
import json
import requests
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
from typing import Dict, List

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api-v3.mbta.com"

CONF_API_KEY = "api_key"

CONF_TRIPS = "trips"

CONF_NAME = "name"
CONF_ROUTE = "route"
CONF_DEPART_FROM = "depart_from"
CONF_ARRIVE_AT = "arrive_at"
CONF_ROUND_TRIP = "round_trip"
CONF_TIME_OFFSET = "offset_minutes"
CONF_TRIPS_LIMIT = "trips_limit"

SCAN_INTERVAL = timedelta(seconds=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_TRIPS): [
            {
                vol.Optional(CONF_NAME, default="MBTA"): cv.string,
                vol.Required(CONF_DEPART_FROM): cv.string,
                vol.Required(CONF_ARRIVE_AT): cv.string,
                vol.Required(CONF_ROUTE): cv.string,
                vol.Optional(CONF_ROUND_TRIP, default=False): cv.boolean,
                vol.Optional(CONF_TIME_OFFSET, default=0): cv.positive_int,
                vol.Optional(CONF_TRIPS_LIMIT, default=2): cv.positive_int,
            }
        ]
    }
)

ROUTE_TYPES = {
    0: "LightRail",
    1: "HeavyRail",
    2: "CommuterRail",
    3: "Bus",
    4: "Ferry"
}

API_KEY = {}

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MBTALive sensor"""

    global API_KEY
    API_KEY = config.get(CONF_API_KEY)

    route_data = populate_routes_data()
    stops_by_route = {}

    sensors = []
    for next_trip in config.get(CONF_TRIPS):
        name = next_trip.get(CONF_NAME)
        route = next_trip.get(CONF_ROUTE)
        depart_from = next_trip.get(CONF_DEPART_FROM)
        arrive_at = next_trip.get(CONF_ARRIVE_AT)
        time_offset_min = next_trip.get(CONF_TIME_OFFSET)
        trips_limit = next_trip.get(CONF_TRIPS_LIMIT)

        stops_by_route = populate_stops_data(stops_by_route, route_data[route]['id'])

        sensors.append(MBTALiveSensor(name, route, depart_from, arrive_at, time_offset_min, trips_limit, route_data, stops_by_route))
        if next_trip.get(CONF_ROUND_TRIP):
            sensors.append(MBTALiveSensor(name+"_back", route, arrive_at, depart_from, time_offset_min, trips_limit, route_data, stops_by_route))
    
    add_entities(sensors, True)

def populate_routes_data() -> Dict:
    """Fetches routes data.
    
    Returns:
        A dictionary of route details indexed by route name.
    """
    url = f"{BASE_URL}/routes"
    params = {
        "include": "stop",
        "fields[route]": "color,long_name,id,type",
        "api_key": API_KEY
    }
    
    _LOGGER.debug("Fetching routes data")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Error fetching route data: %s", e)
        raise

    response_data = response.json()
    
    routes = {route['attributes']['long_name']: {
        'id': route['id'],
        'color': route['attributes']['color'],
        'type': route['attributes']['type']
    } for route in response_data['data']}
    
    _LOGGER.debug(f"Fetched {len(routes)} routes")
    
    return routes

def populate_stops_data(stops_by_route: Dict, route_id: str) -> Dict[str, Dict[str, List[str]]]:
    """Fetches stops data for a given route.

    Args:
        route_id: Route id

    Returns:
        A dictionary of routes, where each route has a dictionary of stop names
        to a list of child stop IDs.
    """
    if route_id in stops_by_route:
        _LOGGER.debug(f"Stops for {route_id} already fetched, skip")
        return stops_by_route
    
    url = f"{BASE_URL}/stops"
    params = {
        "include": "child_stops",
        "filter[route]": route_id,
        "api_key": API_KEY
    }

    _LOGGER.debug(f"Fetching stops for route {route_id}")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        response_data = response.json()
    except requests.exceptions.RequestException as e:
        _LOGGER.error(f"Error fetching stops data for route {route_id}: {e}")
        raise

    stops_by_route[route_id] = {}

    for stop_data in response_data['data']:
        stop_name = stop_data['attributes']['name']
        stops_by_route[route_id][stop_name] = {}
        stop_id = stop_data['id']
        stops_by_route[route_id][stop_name]["stop_id"] = stop_id
        child_stop_ids = [child['id'] for child in stop_data['relationships']['child_stops']['data']]
        if len(child_stop_ids) == 0:
            child_stop_ids = [] 
        stops_by_route[route_id][stop_name]["stop_child_ids"] = child_stop_ids            

    _LOGGER.debug(f"Fetched {len(stops_by_route[route_id])} stops for route {route_id}")

    return stops_by_route

def get_schedules_data(route_id: str, depart_from_stop_ids: List[str], arrive_at_stop_ids: List[str]) -> Dict:
    """Fetches schedule data for given route and stops
    
    Args:
        route_id: The id of the route
        depart_from_stop_ids: The ids of the departing stops
        arrive_at_stop_ids: The ids of the arriving stops
        local_timezone: The timezone to adjust the time

    Returns:
        A dictionary of schedule details indexed by route name.
    """

    url = f"{BASE_URL}/schedules"
    params = {
        "sort": "arrival_time",
        "include": "trip,prediction",
        "filter[min_time]": get_current_time_hhmm(), 
        "filter[date]": get_current_date_yyyymmdd(),
        "filter[route]": route_id,
        "filter[stop]": depart_from_stop_ids+","+arrive_at_stop_ids,
        "api_key": API_KEY
    }

    _LOGGER.debug(f"Fetching schedules, trips, and predictions data for route {route_id} depart from {depart_from_stop_ids} arriving at {arrive_at_stop_ids}")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Error fetching schedule data: %s", e)
        raise
    
    response_data = response.json()
    
    return response_data

def get_schedules(scheduled_data: Dict) -> Dict:
    """Extracts schedules from the scheduled data.

    Args:
        scheduled_data: The input data containing trip information.

    Returns:
        A list of dictionaries, each representing a trip with various schedules attributes.
    """
    
    schedules = {}

    for item in scheduled_data['data']:
        if item['type'] == 'schedule':
            trip_id = item['relationships']['trip']['data']['id']
            schedule_data = {
                'scheduled_id': item['id'],
                'route_id': item['relationships']['route']['data']['id'],
                'trip_id': item['relationships']['trip']['data']['id'],
                'stop_id': item['relationships']['stop']['data']['id'],
                'arrival_time': item['attributes']['arrival_time'],
                'departure_time': item['attributes']['departure_time'],
                'direction_id': item['attributes']['direction_id'],
                'stop_sequence': item['attributes']['stop_sequence'],
                'prediction_data': item['relationships']['prediction'].get('data')
            }
            if trip_id not in schedules:
                schedules[trip_id] = []
            schedules[trip_id].append(schedule_data)
    
    # Sort the schedule data by stop_sequence for each trip_id
    for trip_id in schedules:
        schedules[trip_id].sort(key=lambda x: x['stop_sequence'])
            
    return schedules

def get_trips(scheduled_data: Dict) -> Dict:
    """Extracts trips from the scheduled data.

    Args:
        scheduled_data: The input data containing trip information.

    Returns:
        A list of dictionaries, each representing a trip with various attributes.
    """

    trips = {}

    for item in scheduled_data['included']:
        if item['type'] == 'trip':
            trip_id = item['id']
            trip_data = {
                'route_id': item['relationships']['route']['data']['id'],
                'direction_id': item['attributes']['direction_id'],
                'name': item['attributes']['name'],
                'headsign': item['attributes']['headsign'] 
            }
            trips[trip_id] = trip_data  # Use direct assignment instead of appending to a list
    
    return trips

def get_predictions(scheduled_data: Dict) -> Dict:
    """Extracts schedules from the scheduled data.

    Args:
        scheduled_data: The input data containing trip information.

    Returns:
        A list of dictionaries, each representing a prediction with various attributes.
    """

    predictions = {}

    for item in scheduled_data['included']:
        if item['type'] == 'prediction':
            prediction_id = item['id']
            prediction_data = {
                'stop_id': item['relationships']['stop']['data']['id'],        
                'trip_id': item['relationships']['trip']['data']['id'],
                'arrival_time': item['attributes']['arrival_time'],
                'arrival_uncertainty': item['attributes']['arrival_uncertainty'],
                'departure_time': item['attributes']['departure_time'],
                'departure_uncertainty': item['attributes']['departure_uncertainty'],
            }
            predictions[prediction_id] = prediction_data

    return predictions

def get_stop_timings(stops, predictions) -> List:
    """Get timings for stops list based on predictions."""
    stop_timings = []
    
    for i in [0,1]:
        stop = stops[i]
        
        _LOGGER.debug("stop_id: %s", stop['stop_id'])
        
        if stop["arrival_time"] is not None:
            scheduled_arrival_time = stop["arrival_time"]
            expected_arrival_time = scheduled_arrival_time

            if stop["prediction_data"]:
                prediction_id = stop["prediction_data"]["id"]
                predicted_arrival_time = predictions.get(prediction_id, {}).get("arrival_time")
                expected_arrival_time = predicted_arrival_time or scheduled_arrival_time
                
                arrival_uncertainty = predictions.get(prediction_id, {}).get("arrival_uncertainty")
                _LOGGER.debug("arrival_uncertainty: %s", arrival_uncertainty)
            
            delta_to_scheduled_arrival = (datetime_from_str(expected_arrival_time) - datetime_from_str(scheduled_arrival_time))
            time_until_arrival = (datetime_from_str(expected_arrival_time) - get_current_time())

            _LOGGER.debug("expected_arrival_time: %s", expected_arrival_time)
            _LOGGER.debug("delta_to_scheduled_arrival: %s", delta_to_scheduled_arrival)
            _LOGGER.debug("time_until_arrival: %s", time_until_arrival)

            timing_data = {
                'stop_id': stops[i]['stop_id'],
                'expected_time': expected_arrival_time,
                'delta_to_scheduled': delta_to_scheduled_arrival,
                'time_left': time_until_arrival
            }
    
        else:
        # if stop["departure_time"] is not None:
            scheduled_departure_time = stop["departure_time"]
            expected_departure_time = scheduled_departure_time

            if stop["prediction_data"]:
                prediction_id = stop["prediction_data"]["id"]
                predicted_departure_time = predictions.get(prediction_id, {}).get("departure_time")
                expected_departure_time = predicted_departure_time or scheduled_departure_time
                
                departure_uncertainty = predictions.get(prediction_id, {}).get("departure_uncertainty")
                _LOGGER.debug("departure_uncertainty: %s", departure_uncertainty)
            
            delta_to_scheduled_departure = (datetime_from_str(expected_departure_time) - datetime_from_str(scheduled_departure_time))
            time_until_departure = (datetime_from_str(expected_departure_time) - get_current_time())

            _LOGGER.debug("expected_departure_time: %s", expected_departure_time)
            _LOGGER.debug("delta_to_scheduled_departure: %s", delta_to_scheduled_departure)
            _LOGGER.debug("time_until_departure: %s", time_until_departure)

            timing_data = {
                'stop_id': stops[i]['stop_id'],
                'expected_time': expected_departure_time,
                'delta_to_scheduled': delta_to_scheduled_departure,
                'time_left': time_until_departure
            }
            
        stop_timings.append(timing_data)
    
    return stop_timings

def convert_timedelta_to_string(delta: timedelta) -> str:
    """Converts a timedelta object into a human-readable ETA string.

    Args:
        delta: A timedelta object.

    Returns:
        A string representing the estimated time of arrival.
    """
    is_negative = delta.total_seconds() < 0
    delta = abs(delta)

    total_seconds = int(delta.total_seconds())
    years, remainder = divmod(total_seconds, 31536000)  # 365 days per year
    months, remainder = divmod(remainder, 2592000)  # 30 days per month
    days, remainder = divmod(remainder, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if years:
        parts.append(f"{years} {'year' if years == 1 else 'years'}")
    if months:
        parts.append(f"{months} {'month' if months == 1 else 'months'}")
    if days:
        parts.append(f"{days} {'day' if days == 1 else 'days'}")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")

    result = ' '.join(parts) or "0s"
    if is_negative:
        result = f"-{result}"

    return result

def datetime_from_str(str_datetime:str) -> datetime:
    try:
        return datetime.fromisoformat(str_datetime)
    except ValueError as e:
        _LOGGER.error("Invalid datetime format: %s", e)
        raise
        
def get_current_time() -> datetime:
    """Return the current datetime"""
    return datetime.now().astimezone()

def get_current_time_hhmm() -> str:
    """Return the current time in HH:MM format."""
    return get_current_time().strftime("%H:%M")

def get_current_date_yyyymmdd() -> str:
    """Return the current date in YYYY-MM-DD format."""
    return get_current_time().strftime("%Y-%m-%d")

class MBTALiveSensor(Entity):
    """Implementation of an MBTALive sensor"""

    def __init__(self, name, route, depart_from, arrive_at, time_offset_min, trips_limit, route_data, stops_data):
        """Initialize the sensor"""
        self._name = f"mbta_{depart_from}_to_{arrive_at}".replace(' ', '_') if name == "MBTA" else name
        self._route = route
        self._depart_from = depart_from
        self._arrive_at = arrive_at
        self._time_offset_sec = time_offset_min * 60
        self._trips_limit = trips_limit
        self._transit_color = route_data[self._route]['color']
        self._transit_type = route_data[self._route]['type']
        self._arrival_data = []
        self._route_data = route_data
        self._stops_data = stops_data
        
        self._state = None
        self._arrival_data = []
        self._icon = "mdi:calendar-clock"

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._name

    @property
    def state(self):
        """Return the state"""
        _LOGGER.debug("Returning state")
        if len(self._arrival_data) == 0:
            return "Nothing Scheduled"
        else:
            _LOGGER.debug("time_left: %s", self._arrival_data[0]['time_left'])
            return self._arrival_data[0]['time_left']

    @property
    def extra_state_attributes(self):
        """Return attributes."""
        _LOGGER.debug("Returning attributes")
        if len(self._arrival_data) == 0:
            return {
                "route": self._route,
                "destination": "N/A",
                "depart from": self._depart_from,
                "arrive at": self._arrive_at,
                "expected departure time": "N/A",
                "delay": "N/A",
                "upcoming_departures": "N/A",
                "route type": self._transit_type,
                "route color": self._transit_color,
            }
        else:
            return {
                "route": self._route,
                "destination": self._arrival_data[0].get('trip_to', 'Unknown'),
                "depart from": self._depart_from,
                "arrive at": self._arrive_at,
                "expected departure time": self._arrival_data[0].get('expected_time', 'Unknown'),
                "delay": self._arrival_data[0].get('delta_to_scheduled', 'Unknown'),
                "upcoming_departures": self._arrival_data[1:],
                "route type": self._transit_type,
                "route color": self._transit_color,
            }


    def update(self):
        """Get the latest data and update the state."""
        
        self._arrival_data = []  # Reset arrival data at the beginning of the update


        #get route, depart and arrival stop info from user data
        route_id = self._route_data[self._route]['id']
        depart_from_stop = self._stops_data[route_id][self._depart_from]["stop_id"]
        arrive_at_stop = self._stops_data[route_id][self._arrive_at]["stop_id"]

        schedules_data = get_schedules_data(route_id, depart_from_stop, arrive_at_stop)

        # If there is at least 1 scheduled trip on the route from depart_from to arrive_at
        if len(schedules_data['data']) > 0:
            schedules = get_schedules(schedules_data)
            trips = get_trips(schedules_data)
            predictions = get_predictions (schedules_data)
            
            depart_from_ids = self._stops_data[route_id][self._depart_from].get("stop_child_ids", []) or [self._stops_data[route_id][self._depart_from].get("stop_id")]
            
            i = 0
            # For each scheduled trip   
            for trip_id, stops in schedules.items():
                headsign = trips[trip_id].get('headsign', None)
                logging.debug("Trip %s to %s", trip_id, headsign)

                # If the trip stops at both depart_from and arrive_at, if not it has already left
                if len(stops) == 2:
                    
                    # If the trip is starting from depart_drom, if not is in the wrong direction
                    if stops[0]["stop_id"] in depart_from_ids :
                        timing = get_stop_timings(stops,predictions)
                        
                        time_offset_delta = timedelta(seconds=self._time_offset_sec)
                        if timing[0]['time_left'] > time_offset_delta:
                    
                            self._arrival_data.append({
                                'trip_to': trips[trip_id]['headsign'],
                                'expected_time': timing[0]['expected_time'],
                                'delta_to_scheduled': convert_timedelta_to_string(timing[0]['delta_to_scheduled']),
                                'time_left': convert_timedelta_to_string(timing[0]['time_left'])
                            })

                            _LOGGER.debug("arrival_data %s ", self._arrival_data)

                            i += 1
                            if i > self._trips_limit +1:
                                break
                        
                    else:
                        _LOGGER.debug("Trip %s is in the wrong direction", trip_id)                       
                else:
                    _LOGGER.debug("Trip %s already left %s",trip_id,self._depart_from )

        else:
            _LOGGER.debug("No schedules for %s departing from %s and arriving at %s", self._route, self._depart_from, self._arrive_at ) 