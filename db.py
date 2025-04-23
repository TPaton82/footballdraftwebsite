import pandas as pd
from utils.utils import send_telegram_message
from utils.config import NUM_PLAYERS, ALL_EVENTS
import utils.api as fb_api
from numpy import random


def create_user(conn, name, password_hash, salt, hash_algo, iterations):
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (name, password_hash, salt, hash_algo, iterations) VALUES (%s, %s, %s, %s, %s)",
            (name, password_hash, salt, hash_algo, iterations)
        )

        cursor.connection.commit()


def get_user(conn, name):
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT user_id, name, password_hash, salt, hash_algo, iterations FROM users WHERE name = %s", (name,))
        ret = cursor.fetchone()

    if ret is None:
        return None
    
    return {
        "user_id": ret[0], 
        "name": ret[1], 
        "password_hash": ret[2], 
        "salt": ret[3], 
        "hash_algo": ret[4], 
        "iterations": ret[5]
    }


def get_all_user_ids(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

    return sorted([user[0] for user in users])


def get_player_info(conn, name):
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM players WHERE name = %s", (name,))
        record = cursor.fetchone()

    return {
        "player_id": record[0], 
        "name": record[1], 
        "position": record[2], 
        "headshot": record[3], 
        "team_id": record[4]
    }


def get_all_players(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM players")
        players = cursor.fetchall()

    return sorted([player[1] for player in players])


def get_draft_order(conn):
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                u.name, 
                d.draft_id 
            FROM users u 
                inner join draft d on u.user_id = d.user_id
        """
        )
        draft_data = cursor.fetchall()

        draft_order = []
        for item in draft_data:
            draft_order.append({'Name': item[0], 'Order': item[1]})

    draft_order_df = pd.DataFrame(draft_order, columns=["Name", "Order"]).sort_values('Order')

    full_draft_order = []
    for idx in range(1, NUM_PLAYERS + 1, 1):
        if idx % 2 == 0:
            full_draft_order.append(draft_order_df.sort_values("Order", ascending=False))
        else:
            full_draft_order.append(draft_order_df.sort_values("Order", ascending=True))

    full_draft_order = pd.concat(full_draft_order).reset_index(drop=True)

    return full_draft_order


def remove_pick(conn, name, pick):
    with conn.cursor() as cursor:

        cursor.execute(f"SELECT user_id FROM users where name = %s;", (name,))
        user = cursor.fetchone()

        cursor.execute(f"SELECT player_id FROM players where name = %s;", (pick,))
        player = cursor.fetchone()

        cursor.execute(f"DELETE FROM picks WHERE user_id=%s AND player_id=%s", (user['user_id'], player['player_id']))

    conn.commit()



def calculate_next_gameweek(date: pd.Timestamp) -> str:
    """
    Calculate the next gameweek from a given date.

    :param date: The date to calculate with.
    :return: The next gameweek.
    """
    return date.strftime("%Y-%m-%d %H:%M:%S") if date else None


def add_draft_pick(conn, name, pick):
    with conn.cursor() as cursor:

        cursor.execute(f"SELECT user_id FROM users where name = %s;", (name,))
        user = cursor.fetchone()

        cursor.execute(f"SELECT player_id FROM players where name = %s;", (pick,))
        player = cursor.fetchone()

        # Can default to 1 for draft picks.
        cursor.execute(f"INSERT INTO picks (user_id, player_id, gameweek_id) VALUES(%s, %s, %s)", (user, player, 1))

    conn.commit()

    send_telegram_message(f"`{name}` has picked `{pick}`")


def get_user_gameweek_picks(conn, name, gameweek_id):
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                pl.* 
            FROM users u
                INNER JOIN picks pi ON u.user_id = pi.user_id
                INNER JOIN players pl ON pi.player_id = pl.player_id
            WHERE u.name = %s
            AND pi.gameweek_id = %s;
        """, 
            (name, gameweek_id)
        )

        picks = cursor.fetchall()

    return picks


def get_all_gameweek_picks(conn, gameweek_id):
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                pl.* 
            FROM users u
                INNER JOIN picks pi ON u.user_id = pi.user_id
                INNER JOIN players pl ON pi.player_id = pl.player_id
            WHERE pi.gameweek_id = %s;
        """, 
            (gameweek_id,)
        )

        picks = cursor.fetchall()

    return picks


def get_next_to_pick(conn, draft_order):
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                u.name,
                pl.name as player_name 
            FROM users u
                INNER JOIN picks pi ON u.user_id = pi.user_id
                INNER JOIN players pl ON pi.player_id = pl.player_id
        """
        )
        picks = cursor.fetchall()

        all_picks = []
        for item in picks:
            all_picks.append({'Name': item[0], 'Player': item[1]})

    next_to_pick = draft_order.loc[len(all_picks)].Name

    return next_to_pick


def get_all_player_points(conn):
    """Return all player points"""
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                pl.name,
                pl.headshot,
                pl.position,
                t.name as team_name,
                SUM(value) as total_points
            FROM players pl
                INNER JOIN teams t on t.team_id = pl.team_id
                LEFT JOIN points po ON pl.player_id = po.player_id
                LEFT JOIN events e ON e.event_id = po.event_id
            GROUP BY pl.name, pl.headshot, pl.position, t.name
        """
        )
        data = cursor.fetchall()

        points = []
        for item in data:
            points.append({
                'Name': item[0], 
                'Headshot': item[1], 
                'Position': item[2], 
                'TeamName': item[3], 
                'TotalPoints': item[4] if item[4] is not None else 0
            })

    return pd.DataFrame(
        points, 
        columns=["Name", "Position", "TeamName", "TotalPoints"]
    ).sort_values('TotalPoints', ascending=False)


def set_draft_order(conn):
    """Set the draft order for all existing users"""
    with conn.cursor() as cursor:

        # Delete any existing draft orders
        cursor.execute(f"DELETE FROM draft;")

        # Get all users
        user_ids = get_all_user_ids(conn)
        if len(user_ids) != NUM_PLAYERS:
            return f"Number of users is not equal to {NUM_PLAYERS}!"
        
        # generate a random draft order
        order = random.permutation(NUM_PLAYERS) + 1
        order = {order[i]: user_ids[i] for i in range(len(order))}

        # Now add the new order
        draft_str = [f"({ord}, {user})" for ord, user in order.items()]
        cursor.execute("INSERT INTO draft (draft_id, user_id) VALUES " + ",".join(draft_str))

        conn.commit()

    return "Draft order set successfully!"

def get_standings(conn):
    """Get the current standings"""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
                SELECT 
                    u.name,
                    gw.gameweek_id,
                    pl.name as player_name,
                    pl.position,
                    IFNULL(sum(e.value), 0) as points
                FROM users u
                    INNER JOIN picks pi ON pi.user_id = u.user_id
                    INNER JOIN gameweeks gw on gw.gameweek_id = pi.gameweek_id
                    INNER JOIN players pl on pl.player_id = pi.player_id
                    LEFT JOIN points po on po.player_id = pl.player_id
                    LEFT JOIN events e on e.event_id = po.event_id
                GROUP BY u.name, player_name, gw.gameweek_id, position
            """
        )
        data = cursor.fetchall()

        total_points = []
        for item in data:
            total_points.append({
                'Name': item['name'], 
                'TotalPoints': item['points']
            })

    return pd.DataFrame(
        total_points, 
        columns=["Name", "TotalPoints"]
    ).sort_values('TotalPoints', ascending=False)


def get_live_games(conn, current_time: pd.Timestamp):
    with conn.cursor() as cursor:
        max_time_str = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        min_time_str = (current_time - pd.Timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
        cursor.execute(f"SELECT fixture_id FROM games where {min_time_str - pd.Timedelta(hours=3)} <= start_time <= {max_time_str}")
        all_games = cursor.fetchall()
        fixture_ids = [game['fixture_id'] for game in all_games]

    return fixture_ids


def update_points_for_fixture(conn, fixture_id):
    """Check if there are new events for the given fixture and update database accordingly"""
    events = fb_api.get_all_events_for_fixture(fixture_id)
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT MAX(event_time) FROM points WHERE fixture_id = %s", (fixture_id,))
        latest_event = cursor.fetchall()

        # Then this is the first update, add all events
        if not latest_event:
            cursor.execute("INSERT INTO points (fixture_id, player_id, event_id, event_time) VALUES (%s, %s, %s, %s)", events)
            conn.commit()
        else:
            new_events = events[events['event_time'] > latest_event[0]['event_time']]
            cursor.execute("INSERT INTO points (fixture_id, player_id, event_id, event_time) VALUES (%s, %s, %s, %s)", new_events)
            conn.commit()

    return len(events) == 0


def refresh_data(conn):
    """Refresh events data"""
    fixture_ids = get_live_games(conn, pd.Timestamp.now())

    for fixture_id in fixture_ids:
        update_points_for_fixture(conn, fixture_id)


def initialize_tables(conn, league_id, year, refresh=False):
    """Create all tables if they do not exist, needs to be run before Draft can start and will likely max out API calls"""
    with conn.cursor() as cursor:

        # First check if the tables already exist
        cursor.execute(f"SELECT * FROM games")
        games = cursor.fetchone()

        cursor.execute(f"SELECT * FROM teams")
        teams = cursor.fetchone()

        cursor.execute(f"SELECT * FROM players")
        players = cursor.fetchone()

        cursor.execute(f"SELECT * FROM events")
        events = cursor.fetchone()

        if (games or teams or players or events) and not refresh:
            return "Tables already exist, will not continue unless `refresh` is set to True."

        # Now create the tables
        all_fixtures_df = fb_api.get_all_fixtures(league_id, year)
        print(f"Found {len(all_fixtures_df)} fixtures, Now getting teams information...")

        all_gameweeks_df = all_fixtures_df.groupby(["gameweek_id", "round"]).agg({"start_time": "min"}).reset_index()
        all_gameweeks_df["start_time"] = all_gameweeks_df["start_time"].dt.floor("D")
        all_gameweeks_df['end_time'] = all_gameweeks_df['start_time'].shift(-1).fillna(pd.to_datetime("2200-01-01"))

        all_teams_df = fb_api.get_all_teams(league_id, year)
        print(f"Found {len(all_teams_df)} teams, now getting players information...")

        all_players_df = fb_api.get_all_players(all_teams_df['team_id'].tolist())
        print(f"Found {len(all_players_df)} players")

        print(f"Updating tables...")

        all_fixtures_df = all_fixtures_df.merge(all_teams_df, left_on='home_team_name', right_on='name', how='left')
        all_fixtures_df.rename(columns={"team_id": "home_team_id"}, inplace=True)
        all_fixtures_df = all_fixtures_df.merge(all_teams_df, left_on='away_team_name', right_on='name', how='left')
        all_fixtures_df.rename(columns={"team_id": "away_team_id"}, inplace=True)
        all_fixtures_df = all_fixtures_df[['fixture_id', 'home_team_id', 'away_team_id', 'start_time', 'gameweek_id']]
        all_fixtures_df["start_time"] = all_fixtures_df["start_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        all_teams_df = all_teams_df[['team_id', 'name', 'logo']]

        all_fixtures = [str(tuple(x)) for x in all_fixtures_df.to_numpy()]
        all_gameweeks = [str(tuple(x)) for x in all_gameweeks_df.to_numpy()]
        all_teams = [str(tuple(x)) for x in all_teams_df.to_numpy()]
        all_players = [str(tuple(x)) for x in all_players_df.to_numpy()]
        
        cursor.execute("TRUNCATE TABLE games;")
        cursor.execute("INSERT INTO games (game_id, home_team_id, away_team_id, start_time, gameweek_id) VALUES " + ",".join(all_fixtures))
        print("Updated games table")

        cursor.execute("TRUNCATE TABLE gameweeks;")
        cursor.execute("INSERT INTO gameweeks (gameweek_id, name, start_time, end_time) VALUES " + ",".join(all_gameweeks))
        print("Updated games table")

        cursor.execute("TRUNCATE TABLE teams;")
        cursor.execute("INSERT INTO teams (team_id, name, logo) VALUES " + ",".join(all_teams))
        print("Updated teams table")

        cursor.execute("TRUNCATE TABLE players;")
        cursor.execute("INSERT INTO players (player_id, name, position, headshot, team_id) VALUES " + ",".join(all_players))
        print("Updated players table")

        cursor.execute("TRUNCATE TABLE events;")
        cursor.execute("INSERT INTO events (name, position, value) VALUES " + ",".join([str(event) for event in ALL_EVENTS]))
        print("Updated events table")

        conn.commit()

    return "Tables created successfully!"

