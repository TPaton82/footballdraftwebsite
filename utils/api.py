import requests
import pandas as pd
from utils.config import API_URL, API_LEAGUE_ID, YEAR
from utils.utils import get_cloud_secret

API_KEY = get_cloud_secret("API_KEY")

HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

def get_events_for_fixture(fixture_id):
    response = requests.request("GET", API_URL + f"/fixtures/events?fixture={fixture_id}", headers=HEADERS)
    events = response.json()['response']

    all_events = []
    for event in events:
        all_events.append({
            "Player": event["player"]["name"],
            "Type": event["type"],
            "Time": event["time"]["elapsed"]
        })


def get_fixtures_for_league(league_name):
    response = requests.request("GET", API_URL + f"fixtures?league={API_LEAGUE_ID}&season={YEAR}", headers=HEADERS)
    fixtures = response.json()['response']

    all_fixtures = []
    for fixture in fixtures:
        all_fixtures.append({
            "api_event_id": fixture["fixture"]["id"],
            "start_time": fixture["fixture"]["date"],
            "home_team_name": fixture["teams"]["home"]["name"]
            "away_team_name": fixture["teams"]["away"]["name"]
        })