import requests
from collections import defaultdict
from google.cloud import secretmanager
from utils.config import PROJECT_ID, TELEGRAM_CHAT_ID, TELEGRAM_URL, MAX_PICKS
import os
import pandas as pd
import hashlib
from typing import List, Dict, Tuple



def send_telegram_message(text):
    """Send message to Telegram Group"""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    requests.post(TELEGRAM_URL, json=payload)


def get_cloud_secret(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest")
    return response.payload.data.decode("UTF-8")


def create_secure_password(password, secret_key, hash_algo="sha256", iterations=100000):
    salt = os.urandom(16)

    hash_value = hashlib.pbkdf2_hmac(
        hash_algo,
        password.encode('utf-8') + secret_key.encode('utf-8'),
        salt,
        iterations
    )

    password_hash = salt + hash_value

    return password_hash[:16], password_hash[16:], hash_algo, iterations


def create_path_to_image_html(row):
    """Create a path to image in html format, given a row of the dataframe where the first column contains the name and image path"""
    return f"""
        <div class="image-text-container">
            <img src="{row[0]}" width="60" height="45" class="image">
            <span>{row[1]}</span>
        </div>
    """


# def get_data():
    # data = json.loads(requests.get("https://site.api.espn.com/apis/site/v2/sports/golf/leaderboard").content)
    # competitors = data['events'][0]['competitions'][0]['competitors']

    # output = []
    # for comp in competitors:
    #     name = comp['athlete']['displayName']
    #     pos = comp['status']['position']['displayName']
    #     score = comp['statistics'][0]['displayValue']
    #     thru = comp['status'].get('displayThru', "0").replace("*", "")
    #     headshot = comp['athlete']['headshot']['href']

    #     if thru == "18":
    #         for round_score in comp["linescores"]:
    #             thru = round_score.get('value', thru)

    #     output.append({'name': name, 'headshot': headshot, 'pos': pos, 'thru': int(thru), 'score': score})

    # return output



def validate_pick(player_pick: Dict, existing_picks: List[Dict]) -> Tuple[bool, str]:
    """
    Validate if the player pick is already in the existing picks.

    :param player_pick: The player pick to validate.
    :param existing_picks: List of existing picks.
    :return: True if the pick is valid, False otherwise. With an error message if invalid.
    """
    # Can't pick someone that has been picked already
    print(player_pick)
    print(existing_picks)

    if player_pick["name"] in existing_picks:
        return False, f"{player_pick['name']} has already been picked!"
    
    # Count how many of each pick we have
    freq = defaultdict(Goalkeeper=0, Defender=0, Midfielder=0, Attacker=0)
    for existing_pick in existing_picks:
        freq[existing_pick["position"]] += 1

    # Check if the player pick is valid based on the allowed positions
    player_pos = player_pick["position"]
    num_existing_pos_picks = freq[player_pos]
    
    if num_existing_pos_picks >= MAX_PICKS[player_pos]:
        return False, f"You can only pick {MAX_PICKS[player_pos]} {player_pos} players!"

    return True, ""


def calculate_date_from(date: pd.Timestamp) -> str:
    """
    Calculate the date from a given date.

    :param date: The date to calculate with.
    :return: The calculated date_from as a string.
    """
    return date.strftime("%Y-%m-%d %H:%M:%S") if date else None


def calculate_date_to(date: pd.Timestamp) -> str:
    """
    Calculate the date from a given date.

    :param date: The date to calculate with.
    :return: The calculated date_from as a string.
    """
    return date.strftime("%Y-%m-%d %H:%M:%S") if date else None