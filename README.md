# Football Draft Website

This repository contains the source code for a **Football Draft Website**, a web application designed to manage a fantasy football draft. The application allows users to register, log in, pick players, transfer players, view standings, and more. It is built using Python, Flask, and MySQL, and integrates with external APIs for football data.

## Features

- **User Authentication**: Users can register, log in, and log out securely.
- **Player Drafting**: Users can pick players for their fantasy team in a structured draft order.
- **Player Transfers**: Users can transfer players in and out of their team.
- **Standings**: View the current standings based on player performance.
- **Player Information**: Browse players and their stats.
- **Event Tracking**: View football events and their impact on player points.
- **Admin Setup**: Admins can initialize the draft and refresh data.

### Key Files

- **`main.py`**: The entry point of the application. Defines routes and handles user interactions.
- **`db.py`**: Contains functions for interacting with the MySQL database.
- **`utils/`**: Includes helper functions for API integration, password hashing, and more.
- **`templates/`**: HTML templates for rendering the web pages.
- **`sql/`**: SQL scripts for creating and managing the database schema.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/football-draft-website.git
   cd football-draft-website
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the MySQL database:
   - Import the SQL scripts from the sql/ directory into your MySQL database.

4. Configure secrets
   - Update the utils/config.py file with your project-specific constants

### To Do

- Update Standings to show total, not just gameweeks
- Set up job to get all events for live football games and update points table as required
- Add page to show past and future fixtures, split into game weeks, update with score and scorers etc when available using widgets
- Telegram bot to send messages when it records points for a user
- Add rules page
- Show events page nicely