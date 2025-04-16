import pandas as pd
from utils.utils import send_telegram_message
from utils.config import NUM_PLAYERS
from utils.api import get_events_for_fixture


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
    
    print(ret)

    return {
        "user_id": ret[0], 
        "name": ret[1], 
        "password_hash": ret[2], 
        "salt": ret[3], 
        "hash_algo": ret[4], 
        "iterations": ret[5]
    }


def get_player_info(conn, name):
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM players WHERE name = %s", (name,))
        record = cursor.fetchone()

    return record


def get_all_players(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM players")
        players = cursor.fetchall()

    return sorted([player["name"] for player in players])


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
            draft_order.append({'Name': item['name'], 'Order': item['draft_id']})

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


def add_pick(conn, name, pick):
    with conn.cursor() as cursor:

        cursor.execute(f"SELECT user_id FROM users where name = %s;", (name,))
        user = cursor.fetchone()

        cursor.execute(f"SELECT player_id FROM players where name = %s;", (pick,))
        player = cursor.fetchone()

        cursor.execute(f"INSERT INTO picks (user_id, player_id) VALUES(%s, %s)", (user['user_id'], player['player_id']))

    conn.commit()

    send_telegram_message(f"`{name}` has picked `{pick}`")


def get_user_picks(conn, name):
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                pl.* 
            FROM users u
                INNER JOIN picks pi ON u.user_id = pi.user_id
                INNER JOIN players pl ON pi.player_id = pl.player_id
            WHERE u.name = %s;
        """, 
            (name,)
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
            all_picks.append({'Name': item['name'], 'Player': item['player_name']})

    next_to_pick = draft_order.loc[len(all_picks)].Name

    return next_to_pick


def get_all_player_points(conn):
    """Return all player points"""
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                p.name,
                p.position,
                t.name as team_name
                SUM(point_value) as total_points
            FROM players pl
                INNER JOIN points po ON pl.player_id = po.player_id
                INNER JOIN events e ON e.event_id = po.event_id
                INNER JOIN team t on t.team_id = p.team_id
            GROUP BY p.name, p.position, t.name
        """
        )
        data = cursor.fetchall()

        points = []
        for item in data:
            points.append({
                'Name': item['name'], 
                'Position': item['position'], 
                'TeamName': item['team_name'], 
                'TotalPoints': item['total_points']
            })

    return pd.DataFrame(
        points, 
        columns=["Name", "Position", "TeamName", "TotalPoints"]
    ).sort_values('TotalPoints', ascending=False)


def set_draft_order(conn, order):
    """Set the draft order"""
    with conn.cursor() as cursor:

        # Delete any existing draft orders
        cursor.execute(f"DELETE * FROM draft;")

        # Now add the new order
        to_add = []
        for order, name in order.items():
            cursor.execute(f"SELECT user_id FROM users where name = {name}")
            user = cursor.fetchone()

            if not user:
                raise ValueError(f"No user with name {name}!")

            to_add.append(f"VALUES({order}, {user['user_id']})")

    cursor.execute("INSERT INTO draft (draft_id, user_id) " + ",".join(to_add))

    conn.commit()

def get_total_points(conn):
    """Get the current standings"""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT 
                u.name,
                sum(e.point_value) as points
            FROM users u
                INNER JOIN picks pi ON pi.user_id = u.user_id
                INNER JOIN players pl on pl.player_id = pi.player_id
                INNER JOIN points po on po.player_id = pl.player_id
                INNER JOIN events e on e.event_id = po.event_id
            WHERE po.event_time BETWEEN pi.date_from AND pi.date_to
            GROUP BY u.name
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
        cursor.execute(f"SELECT api_fixture_id FROM games where {min_time_str - pd.Timedelta(hours=3)} <= start_time <= {max_time_str}")
        all_games = cursor.fetchall()
        games = [game['api_fixture_id'] for game in all_games]

    return games


def refresh_data(conn):
    """Refresh events data"""
    with conn.cursor() as cursor:

        games = get_live_games(conn, pd.Timestamp.utcnow())

        for fixture_id in games:
            get_events_for_fixture(fixture_id)

        existing_scoreboard = cursor.fetchall()

        if len(existing_scoreboard) == 0:
            last_update = pd.to_datetime("1970-01-01")
        else:
            last_update = pd.to_datetime(existing_scoreboard[-1]['created_date'])