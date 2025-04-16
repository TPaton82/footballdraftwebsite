import hashlib
import os
import re
from functools import wraps
from math import sqrt
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL

from db import add_pick, remove_pick, get_user_picks, get_draft_order, get_user, create_user, get_player_info, get_next_to_pick, get_all_players, get_all_player_points
from utils.utils import send_telegram_message, get_cloud_secret, create_secure_password, create_path_to_image_html, get_data, refresh_data, validate_pick

app = Flask(__name__)

app.secret_key = get_cloud_secret("FOOTBALL_SECRET_KEY")

if os.environ.get("GAE_ENV") == "standard":
    app.config["MYSQL_UNIX_SOCKET"] = f"/cloudsql/{get_cloud_secret('CLOUD_SQL_CONNECTION_NAME')}"
    app.config["MYSQL_USER"] = get_cloud_secret("CLOUD_SQL_USERNAME")
    app.config["MYSQL_PASSWORD"] = get_cloud_secret("CLOUD_SQL_PASSWORD")
    app.config["MYSQL_DB"] = get_cloud_secret("CLOUD_SQL_DATABASE_NAME")
else:
    app.config["MYSQL_HOST"] = "localhost"
    app.config["MYSQL_USER"] = "root"
    app.config["MYSQL_PASSWORD"] = "password"
    app.config["MYSQL_DB"] = "draft"

# Connect to SQL db
mysql = MySQL(app)

def logged_in(func):
    @wraps(func)
    def check_logged_in():
        # Only show the page if user is logged in
        if 'loggedin' in session:
            return func()

        # User is not loggedin so redirect to login page
        return redirect(url_for('login'))

    return check_logged_in


@app.route('/', methods=['GET', 'POST'])
@logged_in
def landing_page():
    return redirect(url_for("leaderboard"))


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ""

    if request.method == "POST" and "name" in request.form and "password" in request.form:
        # Get the name and password
        name = request.form['name']
        password = request.form['password']

        # Check if account exists
        user = get_user(mysql.connection, name)

        # If account exists show error and validation checks
        if user:
            msg = f"Account with that name already exists!"

        elif not re.match(r'[A-Za-z]+', name):
            msg = 'Name must contain only characters, no numbers or special characters!'

        else:
            # Create hash of password for storage
            salt, password_hash, hash_algo, iterations = create_secure_password(password, app.secret_key)

            # Account doesn't exist, and the form data is valid, so insert the new account into the accounts table
            create_user(mysql.connection, name, password_hash, salt, hash_algo, iterations)
            return render_template('login.html', msg='You have successfully registered!')

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please input Username and Password!'

    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ""

    if request.method == "POST" and "name" in request.form and "password" in request.form:
        # Get the name and password
        name = request.form['name']
        password = request.form['password']

        # Check if user exists
        user = get_user(mysql.connection, name)

        if not user:
            # Account doesn't exist
            msg = 'Incorrect username/password!'
        else:
            # Recompute hash from user entered password
            password_hash = hashlib.pbkdf2_hmac(
                user['hash_algo'],
                password.encode('utf-8') + app.secret_key.encode('utf-8'),
                user['salt'],
                user['iterations']
            )

            # Compare hashes
            if password_hash == user['password_hash']:
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['user_id'] = user['user_id']
                session['username'] = user['username']

                # Redirect to leaderboard
                return redirect(url_for("scores"))
            else:
                msg = 'Incorrect username/password!'

    return render_template("login.html", msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('username', None)

    # Redirect to login page
    return redirect(url_for('login'))


@app.route('/unpick', methods=['GET', 'POST'])
@logged_in
def unpick():
    msg = ""

    if request.method == 'POST' and "name" in request.form and "pick" in request.form:
        name = request.form['name']
        player_pick = request.form['pick']
        remove_pick(mysql.connection, name, player_pick)
        return redirect(url_for("leaderboard"))
    
    elif request.method == "POST":
        msg = "Incorrect username or pick!"

    return render_template("unpick.html", msg=msg)


@app.route('/pick', methods=['GET', 'POST'])
@logged_in
def pick():
    msg = ""

    if request.method == 'POST' and 'player' in request.form:

        draft_order = get_draft_order(mysql.connection)

        # Check to see if it's this users pick next
        next_to_pick = get_next_to_pick(mysql.connection, draft_order)

        if next_to_pick != session["username"]:
            msg = f"It's not your pick, wait for `{next_to_pick}` to pick"

        else:
            # Check to see if we are allowed to pick this player
            player_info = get_player_info(request.form['player'])
            player_existing_picks = get_user_picks(mysql.connection, session["username"])
            valid_pick, error_reason = validate_pick(player_info, player_existing_picks)

            if not valid_pick:
                msg = error_reason
            else:
                add_pick(mysql.connection, session["username"], player_info["name"])

                next_to_pick = get_next_to_pick(mysql.connection, draft_order)
                if next_to_pick is not None:
                    send_telegram_message(f"Waiting for `{next_to_pick}` to pick...")

                return redirect(url_for("leaderboard"))

    all_players = get_all_players(mysql.connection)

    return render_template(
        template_name_or_list="pick.html",
        playerlist=all_players,
        msg=msg
    )


@app.route("/events")
@logged_in
def events():

@app.route("/transfer")
@logged_in
def transfer():


@app.route("/players")
@logged_in
def players():
    """Create players page"""
    player_points = get_all_player_points(mysql.connection)

    return render_template(
        template_name_or_list="players.html",
        scoreboard=(
            player_points
            .to_html(
                index=False,
                escape=False,
                classes='players',
                table_id="players",
                formatters={"Player": create_path_to_image_html}
            )
            .replace('border="1"', 'border="0"')
        )
    )


@app.route("/standings")
@logged_in
def standings():
    """Create leaderboard page"""
    refresh_scoreboard()

    total = get_dd_picks(mysql.connection)
    prizes = get_prizes(mysql.connection)
    scoreboard = get_scoreboard(mysql.connection)

    latest_scores = scoreboard.sort_values('created_date').drop_duplicates(['Player'], keep='last')
    latest_scores_dict = latest_scores.set_index("Player").to_dict()

    total["Position"] = total["Player"].map(latest_scores_dict["Position"])
    total["Score"] = total["Player"].map(latest_scores_dict["Score"])
    total["Headshot"] = total["Player"].map(latest_scores_dict["Headshot"])

    # Calculate earnings for each position (to handle ties)
    calculated_prizes = {}
    calculated_sqrt_prizes = {}
    for pos, data in latest_scores.groupby("Position"):
        # if the position is not tied, just return the prize for that position
        if "T" not in pos:
            calculated_prizes[pos] = prizes.get(pos, 0)
            calculated_sqrt_prizes[pos] = sqrt(prizes.get(pos, 0))

        # Otherwise, calculate the average of all tied players
        else:
            num_players = len(data)
            prize_to_get = str(pos).replace('T', '')
            total_prize = sum([prizes.get(str(int(prize_to_get) + i), 0) for i in range(0, num_players)])
            calculated_prizes[pos] = total_prize // num_players
            calculated_sqrt_prizes[pos] = sqrt(total_prize // num_players)

    # Now apply the calculated prize money to the total DataFrame
    total["Prize Money"] = total["Position"].map(calculated_prizes)
    total["Sqrt Prize Money"] = total["Position"].map(calculated_sqrt_prizes)

    dd_picks = []
    for (name, teamname), df in total.groupby(['Name', 'TeamName']):

        player_standings = {"Name": f"{teamname}<br>({name})"}
        total_sum = 0
        total_sqrt_sum = 0

        for idx, (_, row) in enumerate(df.iterrows(), 1):
            player_standings[f"Pick {idx}"] = [
                row.Headshot, 
                f"{row.Position.replace('-', 'N/A')}: {row['Player']} {row['Score']}<br>{'${:,}'.format(row['Prize Money'])}"
            ]

            total_sum += row['Prize Money']
            total_sqrt_sum += row['Sqrt Prize Money']

        player_standings['TotalInt'] = total_sum
        player_standings['Total'] = "${:,}".format(total_sum)
        player_standings['TotalIntSqrt'] = total_sqrt_sum
        player_standings['TotalSqrt'] = "${:,}".format(int(total_sqrt_sum))
        dd_picks.append(player_standings)

    if len(dd_picks) > 0:
        dd_picks_df = pd.DataFrame(dd_picks).sort_values('Total')
        dd_picks_df.sort_values("TotalIntSqrt", ascending=False, inplace=True)
        player_cols = sorted([col for col in dd_picks_df.columns if "Pick" in col])
        dd_picks_df = dd_picks_df[["Name", "TotalSqrt", "Total"] + player_cols]
    else:
        dd_picks_df = pd.DataFrame()

    return render_template(
        template_name_or_list="leaderboard.html",
        dd_picks=dd_picks_df.to_html(
            index=False,
            escape=False,
            classes='leaderboard',
            formatters={
                "Pick 1": create_path_to_image_html,
                "Pick 2": create_path_to_image_html,
                "Pick 3": create_path_to_image_html,
                "Pick 4": create_path_to_image_html,
                "Pick 5": create_path_to_image_html
            }
        )
        .replace('border="1"', 'border="0"')
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
