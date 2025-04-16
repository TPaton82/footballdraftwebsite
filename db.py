import pandas as pd
from utils.utils import send_telegram_message
from utils.config import DRAFT_PICKS


def create_user(conn, name, password_hash, salt, hash_algo, iterations):
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (name, password_hash, salt, hash_algo, iterations) VALUES (%s, %s, %s, %s, %s)",
            (name, password_hash, salt, hash_algo, iterations)
        )

        cursor.connection.commit()


def get_user(conn, name):
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM users WHERE name = %s", (name,))
        record = cursor.fetchone()

    return record


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
    for idx in DRAFT_PICKS:
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
                u.name,
                pl.name as player_name 
            FROM users u
                INNER JOIN picks pi ON u.user_id = pi.user_id
                INNER JOIN players pl ON pi.player_id = pl.player_id
        """
        )

