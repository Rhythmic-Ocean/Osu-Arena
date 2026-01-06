# 🌀 osu!Arena Discord Bot

![Docs Status](https://img.shields.io/badge/Docs-Work%20In%20Progress-yellow)

> [Website](https://osu-arena.com) | [Join the Discord](https://discord.gg/rskvV32ZmX)

**osu!Arena** is a custom-built, real-time Discord bot designed for the **osu! community** at osu!Arena. It manages league sessions, rivalries, challenges, player verification, and rank syncing for a competitive community racing.

---

## Recent (Jan 2026)

- Completed code refactoring and reinitiated all previous functions.
- New Additions:
  - Basic sphinx docs completed for `utils/db_handler.py`
  - The project now uses docker for better stability
  - Now with persistent views, challenge requests can theoretically last indefinitely.
  - The bot now uses the Cogs model. [Learn More](https://github.com/kkrypt0nn/Python-Discord-Bot-Template)
  - The website uses Quart instead of Flask for proper integration with the async Database Manager.
  - Added several new .html templates to display specific content based on the OAuth error type.
  - Most database modification actions are now performed through Postgres RPC, with a few exceptions.
  - New GitHub workflow for nightly backups (in a private repo).
  - Extended error handling with direct error reporting to the server via WebHook (see more at `utils_v2/log_handling.py`).
  - `web.py` now follows View model to match the bot's class-based architecture. [Learn More](https://flask.palletsprojects.com/en/stable/views/)
  - /link generated URLs are only valid for 5 mins now.
  - The bot and the web app are now hosted on AWS.
  - New website [URL](https://osu-arena.com)

---

## TODO

- Refactor the `supabase.py` cronjob (and rename it) to better align with the rest of the project's architecture.
- Documentation (specifically for `utils_v2/db_handler.py`).

---

## Features

- **osu! Account Linking** – Secure OAuth2-based account verification via website.
- **League System** – Automatically assigns users into leagues (Bronze → Master) based on osu! rank.
- **Rivalry & Challenge System** – Issue & manage direct 1v1 challenges with real-time updates.
- **Live PP & Rank Updates** – Every player’s rank & pp is updated constantly in the database.
- **Session Resets** – Admins can restart sessions to reassign league brackets.
- **Archived Seasons & Challenges** – Access previous seasons and completed rivalries via `/archived` command.
- **Winner Announcements** – Rivalry winners are automatically detected and announced.
- **Asynchronous Architecture** – Uses `asyncio` and parallel modules for optimal performance.
- **OAuth Landing Page** – Hosted with Railway to handle account linking & redirection.

---

## Commands (Help Menu)

The bot uses **slash commands** for a cleaner experience. Here’s what you can do:

---

### `/link`

Link your osu! account securely via OAuth2.  
_All users signed up before **June 18, 2025, 22:50 CDT** were linked manually._

---

### `/show [league]`

Shows the table for a specific league.

- **league**: Available League names: Novice, Bronze, Silver, Gold, Platinum, Diamond, Elite, Ranker(deprecated), Master
- Other miscellaneous table to be accesed: Rivals, Points, S_points.  
  Examples:
- `/show league:Bronze`
- `/show league:Silver`
- `/show league:Rivals`

---

### `/archived [season] [league]`

View archived tables from previous seasons or finished challenges.

- **season**: Season number (integer).
- **league**: League name (e.g., Bronze, Silver, Gold, Rivals, S_points).
- **Note**: `season:0` is the only valid value for `leag:Rivals`.
  Only `season:1` available for Ranker league
  Seasonal_point archives starts from `season:3`
  Archives unavailable for universal points

Examples:

- `/archived season:1 leag:Bronze`
- `/archived season:0 leag:Rivals`
- `/archived season:3 leag:S_points`(when `season:3` ends)

Works only for **finished** seasons and challenges.

---

### `/challenge @user <pp>`

Challenge a player in your league for a match.

- Max **3 active** challenges
- PP must be **250–750**
- You can’t challenge the same player **more than once a day**
- The challenged player gets a DM to accept/decline
- Challenge only valid for 10 mins, gets revoked if not responded within time limit

Example:  
`/challenge player:@Rhythmic_Ocean pp:700`

---

### `/revoke_challenge @user`

Revoke a pending challenge you issued.

- Only **unaccepted (pending)** challenges can be revoked
- If the challenge has been accepted, it **cannot** be revoked

Example:  
`/revoke_challenge player:@Rhythmic_Ocean`

---

### `/session_restart`

Admin-only command to reset the current session, create backups and reassign users to leagues.

---

### `/points @user points`

Restricted to be used by Admin and Speed-rank-judge only
Can add/ remove points for any user
Effects both seasonal and universal points

---

## Project Structure

```

├── bot.py
├── cogs
│   ├── archived.py
│   ├── challenges.py
│   ├── monitor.py
│   ├── player_mgmt.py
│   ├── points.py
│   ├── revoke.py
│   ├── season_restart.py
│   └── show.py
├── compose.yaml
├── Dockerfile
├── load_env.py
├── requirements.txt
├── static
│   └── race_to_4_digit_icon.jpg
├── supaabse.py
├── templates
│   ├── bad_req.html
│   ├── base.html
│   ├── dashboard.html
│   ├── error.html
│   ├── old_account.html
│   ├── too_late.html
│   └── welcome.html
├── utils_v2
│   ├── challenger_viewer.py
│   ├── db_handler.py
│   ├── enums
│   │   ├── status.py
│   │   ├── tables_internals.py
│   │   └── tables.py
│   ├── init_externs.py
│   ├── __init__.py
│   ├── log_handler.py
│   ├── osuapi_handler.py
│   ├── renderer.py
│   ├── reset_utils.py
│   └── supabase_schema.sql
├── web.log
├── web.py
└── web_utils
    ├── web_helper.py
    └── web_viewer.py
```

---

## Stuff Used

- **Python 3.12+**
- **[Discord.py](https://discordpy.readthedocs.io/en/stable/)** – Discord bot framework
- **[Supabase](https://supabase.com)** – Realtime Postgres database
- **[AWS](https://aws.amazon.com/)** – Cloud hosting (used for web and bot deployment)
- **[Pythonanywhere](https://www.pythonanywhere.com/)** – Cloud hosting (used for supaabse.py cronjob)
- **[Quart](https://quart.palletsprojects.com/en/latest/)** – Handles OAuth2 web flow
- **[osu.py](https://github.com/Sheppsu/osu.py)** – Python wrapper for the osu! API
- **[asyncio](https://docs.python.org/3/library/asyncio.html)** – Async tasks, loops, polling
- **[Docker](https://docs.docker.com/)** – Containerized for consistent deployment
- **[Nginx](https://nginx.org/)** – to setup reverse proxy from local port 5000 as well as SSL certification for the domain
- **osu! API v2** – For player stats, rank, and pp data
- **As well as other python libs like plottable.py, panads.py etc... (All in requirements.txt)**

---

## Deployment Overview

> All major modules are deployed separately:

| Component     | Role                                       | Deployment                        |
| ------------- | ------------------------------------------ | --------------------------------- |
| `bot.py`      | Main Discord bot runtime                   | AWS (Bot Host)                    |
| `web.py`      | OAuth2 account linking + redirect handling | AWS (Web App)                     |
| `supaabse.py` | PP/Rank sync for all tracked users         | Pythonanywhere/ cron-job (Worker) |

---

## Local Setup(Linux/ MacOS)

Follow these steps to get a development instance of **osu!Arena** running locally.

### Prerequisites

- Docker
- **Git**
- A **Supabase** project (Free tier works)
- **Discord Application** (Bot Token + Client ID)
- **osu! OAuth Application** (Client ID + Client Secret) x2 (one for background pp updater, one for oauth linker (read on for more detail))

### 1. Fork & Clone

Fork the repository to your GitHub account, then clone it to your local machine:

```bash
# Replace 'YOUR_USERNAME' with your GitHub username
git clone [https://github.com/YOUR_USERNAME/Osu-Arena.git]
cd Osu-Arena
```

### 2. Configuring .env

Create a file named `local.env` in the root directory. Copy and paste the following template, filling in your specific API keys:

```bash
# --- Discord Configuration ---
DISCORD_TOKEN=      # Main authentication token for the Discord bot instance.

# --- osu! OAuth (Web/Linking) ---
AUTH_ID=            # osu! Client ID for handling the initial OAuth2 web linking flow.
AUTH_TOKEN=         # osu! Client Secret for the web linking flow.
REDIRECT_URL=       # The callback URL for OAuth (e.g., http://localhost:5000/callback).

# --- osu! API Clients (Data Fetching) ---
OSU_CLIENT_ID=      # Primary osu! Client ID for general API requests (user stats, etc).
OSU_CLIENT_SECRET=  # Primary osu! Client Secret.
OSU_CLIENT2_ID=     # Secondary osu! Client ID (used for background workers/syncing).
OSU_CLIENT2_SECRET= # Secondary osu! Client Secret.

# --- Database ---
SUPABASE_URL=       # The API URL for your Supabase project.
SUPABASE_KEY=       # The Supabase Service Role key (or Anon key) for DB access.

# --- Security & Encryption ---
QUART_SECKEY=       # Random string to sign session cookies (Run `openssl rand -hex 32`).
SEC_KEY=            # Key used to encrypt/serialize Discord IDs in OAuth URLs.

# --- Guild Configuration (IDs) ---
OSU_ARENA=          # The ID of the main server (Guild) the bot operates in.
REQ_ROLE=           # Role ID required for admin commands (/season_reset, /delete).
REQ_ROLE_POINTS=    # Role ID required for point management commands (/points).

# --- Channels & Webhooks ---
RIVAL_RES_ID=       # Channel ID for posting rival match results.
WELCOME_ID=         # Channel ID for welcome messages.
BOT_UPDATES=        # Channel ID for bot status updates/changelogs.
TOP_PLAY_ID=        # Channel ID for posting new top plays.
LOGS_WEBHOOK=       # Webhook URL for logging errors and info (avoids channel ID usage).
```

### 3. Database Initialization

1. Log in to your Supabase Dashboard.

2. Go to the SQL Editor.

3. Open the file `utils_v2/supabase_schema.sql` located in the root of this repository.

4. Recommended this [Youtube Tutorial](https://www.youtube.com/watch?v=tsw7LzIM5_o) for how you can use the given .sql files to create the required database layout

**NOTE**: `supabase_schema.sql` might be outdated as I'm trying to migrate all my modification type queries to be postgres RPC But I can provide you with the latest one if you ask me

### 4. Running the Bot

The bot and the server will run in different container, all are configured in compose.yaml file

To watch live bot/ web logs:

```bash

docker compose up --watch
```

To let the bot/ web run in the background:

```bash

docker compose up -d
```

### Note: the web is configured to expose itself at port 5000
