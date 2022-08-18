import pandas as pd
import logging
import sys
import requests
import json
import difflib
import inquirer as inq


def get_possible_locations():
    """
    This function creates a dataframe from a json file with information about
    cities, states, latitude, and longitude.  This function also creates a list
    of unique city, state combinations.
    """
    url = 'https://raw.githubusercontent.com/sjlu/cities/master/locations.json'
    loc_df = pd.read_json(url)
    # I am choosing to remove duplicates because I sampled a couple cities and
    # decided the weather doesn't vary too much within the same city.
    loc_df = loc_df.drop_duplicates(subset=['city', 'state'],
                                    keep='first',
                                    inplace=False).reset_index(drop=True)
    # Create a list of possible city, state combinations
    loc_df['city_state'] = loc_df.city + ', ' + loc_df.state
    locations = loc_df['city_state'].tolist()
    return loc_df, locations


def get_city_and_state_from_user(locations):
    """
    This function prompts the user to know which city they want the weather
    for. If the city, state does not exist in the locations list, then it uses
    fuzzy matching to make a suggestion for the user to pick from. This
    function returns the city, state pair.
    """
    city_state = input('What city would you like to know the weather for?\n')
    if city_state in locations:
        return city_state
    else:
        possible_cities = difflib.get_close_matches(city_state,
                                                    locations,
                                                    cutoff=0.5)
        if len(possible_cities) > 0:
            question = [inq.List('city_state',
                                 message="Did you mean one of these cities?.",
                                 choices=possible_cities)]
            return inq.prompt(question).get('city_state')
        else:
            return 'Could not find a city that matches. Please try again.'


def get_lat_and_lon(city_state, loc_df):
    """
    This function takes the user inputted city and state and returns the
    latitude (lat) and longitude (lon) for that city.
    """
    lat = loc_df.latitude[loc_df.city_state == city_state].item()
    lon = loc_df.longitude[loc_df.city_state == city_state].item()
    return lat, lon


def get_grid_information(lat, lon):
    """
    This function takes latitude (lat) and longitude (lon) of the city as an
    input and uses the weather.gov api to pinpoint a grid.  This gives us a
    location of a weather station.
    """
    endpoint = 'https://api.weather.gov/points/%s,%s' \
               % (lat, lon)
    response = requests.get(endpoint)
    response_json = json.loads(response.text)
    if response.status_code == 200:
        grid_id = response_json['properties']['gridId']
        grid_x = response_json['properties']['gridX']
        grid_y = response_json['properties']['gridY']
        return grid_id, grid_x, grid_y
    else:
        logger.critical('API Failed: %s', response.content)
        sys.exit(1)


def get_weather(grid_id, grid_x, grid_y, city_state):
    """
    This function uses the weather.gov api to get the current weather
    information based on weather station locations in the city specified by the
    user.
    """
    endpoint = 'https://api.weather.gov/gridpoints/%s/%s,%s/forecast' \
               % (grid_id, grid_x, grid_y)
    response = requests.get(endpoint)
    if response.status_code == 200:
        response_json = json.loads(response.text)
        periods = response_json['properties']['periods'][0]
        print(str(periods['name']) + ' is ' + str(periods['detailedForecast']))
        return
    else:
        logger.critical("API Failed: %s", response.content)
        sys.exit(1)


def main():
    # Get locations from Github repo
    loc_df, locations = get_possible_locations()
    # Prompt the user for city and state
    city_state = get_city_and_state_from_user(locations)
    # Get latitude and longitude for the user input
    lat, lon = get_lat_and_lon(city_state, loc_df)
    # Get weather station grid informaiton
    grid_id, grid_x, grid_y = get_grid_information(lat, lon)
    # Get and return weather forecast
    get_weather(grid_id, grid_x, grid_y, city_state)


if __name__ == '__main__':
    # logging
    logging.basicConfig(stream=sys.stderr,
                        format='%(levelname)s: %(name)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    main()
