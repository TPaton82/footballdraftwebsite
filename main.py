import hashlib
import os
import re
from functools import wraps
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import db 

from utils.utils import (
    send_telegram_message, 
    get_cloud_secret, 
    create_secure_password, 
    create_path_to_image_html, 
    validate_pick
)

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
    return redirect(url_for("standings"))


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ""

    if request.method == "POST" and "name" in request.form and "password" in request.form:
        # Get the name and password
        name = request.form['name']
        password = request.form['password']

        # Check if account exists
        user = db.get_user(mysql.connection, name)

        # If account exists show error and validation checks
        if user:
            msg = f"Account with that name already exists!"

        elif not re.match(r'[A-Za-z]+', name):
            msg = 'Name must contain only characters, no numbers or special characters!'

        else:
            # Create hash of password for storage
            salt, password_hash, hash_algo, iterations = create_secure_password(password, app.secret_key)

            # Account doesn't exist, and the form data is valid, so insert the new account into the accounts table
            db.create_user(mysql.connection, name, password_hash, salt, hash_algo, iterations)
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
        user = db.get_user(mysql.connection, name)

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
                session['username'] = user['name']

                # Redirect to leaderboard
                return redirect(url_for("standings"))
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
        db.remove_pick(mysql.connection, name, player_pick)
        return redirect(url_for("leaderboard"))
    
    elif request.method == "POST":
        msg = "Incorrect username or pick!"

    return render_template("unpick.html", msg=msg)


@app.route('/pick', methods=['GET', 'POST'])
@logged_in
def pick():
    msg = ""

    if request.method == 'POST' and 'player' in request.form:

        draft_order = db.get_draft_order(mysql.connection)

        # Check to see if it's this users pick next
        next_to_pick = db.get_next_to_pick(mysql.connection, draft_order)

        if next_to_pick != session["username"]:
            msg = f"It's not your pick, wait for `{next_to_pick}` to pick"

        else:
            # Check to see if we are allowed to pick this player
            player_info = db.get_player_info(mysql.connection, request.form['player'])
            player_existing_picks = db.get_user_picks(mysql.connection, session["username"])
            valid_pick, error_reason = validate_pick(player_info, player_existing_picks)

            if not valid_pick:
                msg = error_reason
            else:
                db.add_pick(mysql.connection, session["username"], player_info["name"])

                next_to_pick = db.get_next_to_pick(mysql.connection, draft_order)
                if next_to_pick is not None:
                    send_telegram_message(f"Waiting for `{next_to_pick}` to pick...")

                return redirect(url_for("leaderboard"))

    all_players = db.get_all_players(mysql.connection)

    return render_template(
        template_name_or_list="pick.html",
        playerlist=all_players,
        msg=msg
    )


@app.route("/events")
@logged_in
def events():
    return render_template(
        template_name_or_list="events.html",
        events=(
            pd.DataFrame()
            .to_html(
                index=False,
                escape=False,
                classes='events',
                table_id="events"
            )
            .replace('border="1"', 'border="0"')
        )
    )

@app.route("/transfer")
@logged_in
def transfer():
    msg = ""
    all_players = db.get_all_players(mysql.connection)
    return render_template(template_name_or_list="transfer.html", players=all_players, msg=msg)


@app.route("/rules")
@logged_in
def rules():
    return render_template(template_name_or_list="rules.html")


@app.route("/players")
@logged_in
def players():
    """Create players page"""
    player_points = db.get_all_player_points(mysql.connection)

    return render_template(
        template_name_or_list="players.html",
        players=(
            player_points
            .to_html(
                index=False,
                escape=False,
                classes='players',
                table_id="players",
                #formatters={"Player": create_path_to_image_html}
            )
            .replace('border="1"', 'border="0"')
        )
    )


@app.route("/standings")
@logged_in
def standings():
    """Create standings page"""
    #refresh_data(mysql.connection)

    standings = db.get_standings(mysql.connection)

    return render_template(
        template_name_or_list="standings.html",
        total_points=standings.to_html(
            index=False,
            escape=False,
            classes='standings'
        ).replace('border="1"', 'border="0"')
    )


@app.route("/setup", methods=['GET', 'POST'])
@logged_in
def setup():
    """
    Setup data and create draft order.
    USE CAREFULLY - THIS WILL DELETE ALL DATA IN TABLES AND REFRESH
    """
    msg = ""

    if request.method == 'POST' and 'league_id' in request.form and 'year' in request.form:

        if session["username"] != "Tom":
            msg = "You are not allowed to do this!"
        else:
            league_id = request.form['league_id']
            year = request.form['year']
            msg = db.initialize_tables(mysql.connection, league_id, year, refresh=True)
            msg += db.set_draft_order(mysql.connection)

    return render_template(
        template_name_or_list="setup.html",
        msg=msg
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
