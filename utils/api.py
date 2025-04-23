"""
Functions to get data from the football API.

Notes:
- The API is rate limited to 10 requests per minute
- The API total requests are limited to 100 per day
"""

import requests
import pandas as pd
from utils.config import API_URL, GAMEWEEKS
from utils.utils import get_cloud_secret
from typing import List
from time import sleep

API_KEY = get_cloud_secret("API_KEY")

HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

def get_all_events_for_fixture(fixture_id):
    """Get all events for the given fixture"""
    response = requests.request("GET", API_URL + f"/fixtures/events?fixture={fixture_id}", headers=HEADERS)
    events = response.json()['response']

    all_events = []
    for event in events:
        all_events.append({
            "fixture_id": fixture_id,
            "player": event["player"]["name"],
            "team": event["team"]["name"],
            "type": event["type"],
            "time": event["time"]["elapsed"]
        })

    return all_events


def get_all_fixtures(league_id, year) -> pd.DataFrame:
    """Get all fixtures for the given league for the given year"""
    response = requests.request("GET", API_URL + f"fixtures?league={league_id}&season={year}", headers=HEADERS)
    fixtures = response.json()['response']

    all_fixtures = []
    for fixture in fixtures:
        all_fixtures.append({
            "fixture_id": fixture["fixture"]["id"],
            "start_time": fixture["fixture"]["date"],
            "home_team_name": fixture["teams"]["home"]["name"],
            "away_team_name": fixture["teams"]["away"]["name"],
            "round": fixture["league"]["round"],
        })

    all_fixtures_df = pd.DataFrame(all_fixtures)
    all_fixtures_df['start_time'] = pd.to_datetime(all_fixtures_df['start_time'])
    all_fixtures_df['start_time'] = all_fixtures_df['start_time'].dt.tz_convert('Europe/London').dt.tz_localize(None)

    all_fixtures_df["gameweek_id"] = all_fixtures_df["round"].map(GAMEWEEKS)
    
    if all_fixtures_df["gameweek_id"].isnull().any():
        raise ValueError(f"Some fixtures do not have a gameweek id. Please check the fixtures data. Unique round names are {all_fixtures_df['round'].unique()}")

    return all_fixtures_df


def get_all_teams(league_id, year):
    """Get all teams for the given league for the given year"""
    response = requests.request("GET", API_URL + f"teams?league={league_id}&season={year}", headers=HEADERS)
    teams = response.json()['response']

    all_teams = []
    for team in teams:
        all_teams.append({
            "team_id": team["team"]["id"],
            "name": team["team"]["name"],
            "code": team["team"]["code"],
            "logo": team["team"]["logo"]
        })

    all_teams_df = pd.DataFrame(all_teams)
    
    return all_teams_df


def get_all_players(team_ids: List) -> pd.DataFrame:
    """Get all players for the given team id's"""
    all_players = []
    for team_id in team_ids:
        sleep(10) # To avoid hitting the API rate limit
        response = requests.request("GET", API_URL + f"players/squads?team={team_id}", headers=HEADERS)
        players = response.json()['response'][0]['players']

        for player in players:
            all_players.append({
                "player_id": player["id"],
                "name": player["name"],
                "position": player["position"],
                "headshot": player["photo"],
                "team_id": team_id,
            })

        print(f"Found {len(players)} players for team id: {team_id}")

    all_players_df = pd.DataFrame(all_players)
    
    return all_players_df
