# 🌀 osu!Arena Discord Bot

> [Website](https://rt4d-production.up.railway.app) | [Join the Discord](https://discord.com/invite/GBsNU5hCQy)

**osu!Arena** is a custom-built, real-time Discord bot designed for the **osu! community** at osu!Arena. It manages league sessions, rivalries, challenges, player verification, and rank syncing for a competitive community racing to reach 4-digit osu! global rank and beyond.

---

## Features

-  **osu! Account Linking** – Secure OAuth2-based account verification via website.
-  **League System** – Automatically assigns users into leagues (Bronze → Master) based on osu! rank.
-  **Rivalry & Challenge System** – Issue & manage direct 1v1 challenges with real-time updates.
-  **Live PP & Rank Updates** – Every player’s rank & pp is updated constantly in the database.
-  **Session Resets** – Admins can restart sessions to reassign league brackets.
-  **Archived Seasons & Challenges** – Access previous seasons and completed rivalries via `/archived` command.
-  **Winner Announcements** – Rivalry winners are automatically detected and announced.
-  **Asynchronous Architecture** – Uses `asyncio` and parallel modules for optimal performance.
-  **OAuth Landing Page** – Hosted with Railway to handle account linking & redirection.

---

## Commands (Help Menu)

The bot uses **slash commands** for a cleaner experience. Here’s what you can do:

---

###  `/link`  
Link your osu! account securely via OAuth2.  
_All users signed up before **June 18, 2025, 22:50 CDT** were linked manually._

---

###  `/show [league]`  
Shows the table for a specific league.  
Examples:  
- `/show league:Bronze`  
- `/show league:Silver`  
- `/show league:Rivals`  

Available leagues:  
`Bronze, Silver, Gold, Platinum, Diamond, Elite, Ranker, Master, Rivals`

---

###  `/archived [season] [league]`  
View archived tables from previous seasons or finished challenges.  
- **season**: Season number (integer).  
- **league**: League name (e.g., Bronze, Silver, Gold, Rivals).  
- **Note**: `season:0` is the only valid value for `leag:Rivals`.  

Examples:  
- `/archived season:1 leag:Bronze`  
- `/archived season:0 leag:Rivals`  

Works only for **finished** seasons and challenges.

---

###  `/challenge @user <pp>`  
Challenge a player in your league for a match.  
- Max **3 active** challenges  
- PP must be **250–750**  
- You can’t challenge the same player **more than once a day**  
- The challenged player gets a DM to accept/decline  

Example:  
`/challenge player:@Rhythmic_Ocean pp:700`

---

###  `/revoke_challenge @user`  
Revoke a pending challenge you issued.  
- Only **unaccepted (pending)** challenges can be revoked  
- If the challenge has been accepted, it **cannot** be revoked  

Example:  
`/revoke_challenge player:@Rhythmic_Ocean`

---

###  `!session_restart`  
Admin-only command to reset the current session and reassign users to leagues.

---

## Project Structure
```bash
├── auth.py #The entry point for the bot
├── commands #All commands stored here
│   ├── archived.py
│   ├── challenge.py
│   ├── help.py
│   ├── __init__.py
│   ├── link.py
│   ├── revoke_challenge.py
│   ├── session_restart.py
│   ├── show.py
│   ├── strip.py #this was a one-time command, deprecated for now
│   └── update.py #not a seperate command, runs in sync with session_restart
├── core_web.py #utils for website and linking
├── README.md
├── requirements.txt
├── static 
│   └── race_to_4_digit_icon.jpg
├── supaabse.py #bot that fetches the latest pp for existing players from osu!API and updates it on our database (hosted in pythonanywhere) 
├── supabase_schema.txt #schema of our database tables
├── templates #website templetes 
│   ├── base.html
│   ├── dashboard.html
│   └── welcome.html
├── utils #utils for all commands on commands/ <span style="color:green">Documented</span>
│   ├── archive_utils.py
│   ├── challenge_final.py
│   ├── core_v2.py
│   ├── db_getter.py
│   ├── __init__.py
│   ├── link_utils.py
│   ├── monitoring.py #runs in parallel with the bot. Moniters for any new user after they do /link to make announcement + 
│   │                  monitors for results in rival challenges
│   ├── render.py
│   ├── reset_utils.py
│   ├── rivarly_auth.py
│   └── rivarly_process.py
└── web.py #website's backend 
```
---

## Stuff Used

- **Python 3.12+**
- **[Discord.py](https://discordpy.readthedocs.io/en/stable/)** – Discord bot framework
- **[Supabase](https://supabase.com)** – Realtime Postgres database
- **[Railway](https://railway.app)** – Cloud hosting (used for all deployments)
- **[Flask](https://flask.palletsprojects.com/)** – Handles OAuth2 web flow
- **[osu.py](https://github.com/Sheppsu/osu.py)** – Python wrapper for the osu! API
- **[asyncio](https://docs.python.org/3/library/asyncio.html)** – Async tasks, loops, polling
- **osu! API v2** – For player stats, rank, and pp data
- **As well as other python libs like plottable.py, panads.py etc... (All in requirements.txt)**

---

## Deployment Overview

> All major modules are deployed separately for scalability:

|    Component   |                    Role                        |           Deployment             |
|----------------|------------------------------------------------|----------------------------------|
| `auth.py`      | Main Discord bot runtime                       | Railway (Bot Host)               |
| `web.py`       | OAuth2 account linking + redirect handling     | Railway (Web App)                |
| `supaabse.py`  | PP/Rank sync for all tracked users             | Pythonanywhere/ cron-job (Worker)|



---
## Local Setup

  Follow these steps to get a development instance of **osu!Arena** running locally.

### Prerequisites

- **Python 3.12+**
- **Git**
- A **Supabase** project (Free tier works)
- **Discord Application** (Bot Token + Client ID)
- **osu! OAuth Application** (Client ID + Client Secret) x2 (one for background pp updater, one for oauth linker (read on for more detail))

### 1. Fork & Clone
  Fork the repository to your GitHub account, then clone it to your local machine:

  ```bash
  # Replace 'YOUR_USERNAME' with your GitHub username
  git clone [https://github.com/YOUR_USERNAME/osu-arena-bot.git](https://github.com/YOUR_USERNAME/osu-arena-bot.git)
  cd osu-arena-bot
  ```

### 2. Python Environment Setyp
  It is recommended to use a virtual environment to manage dependencies.
  # Create a virtual environment
  ```bash
  python3 -m venv venv
  ```

  # Activate the environment (Linux/macOS)
  ```bash
  source venv/bin/activate
  ```

  # Install dependencies
  ```bash
  pip install -r requirements.txt
  ```

### 3. Cnfiguring .env
  Create a file named `sec.env` in the root directory. Copy and paste the following template, filling in your specific API keys:

  ```bash

  # --- Discord ---
  DISCORD_TOKEN=      # Main authentication token for the Discord bot instance.

  # --- osu! OAuth (Web/Linking) ---
  AUTH_ID=            # osu! Client ID for handling the initial OAuth2 web linking flow.
  AUTH_TOKEN=         # osu! Client Secret for the web linking flow.

  # --- osu! API (Background Sync) ---
  OSU_CLIENT2_ID=     # Secondary osu! Client ID for the background worker to sync players current_pp.
  OSU_CLIENT2_SECRET= # Secondary osu! Client Secret for background worker to sync players current_pp

  # --- Database ---
  SUPABASE_URL=       # The API URL for your Supabase project
  SUPABASE_KEY=       # The Supabase Service Role key for backend database access

  # --- Security & Encryption ---
  FLASK_SECKEY=       # Random string used to sign and secure Flask session cookies
  SEC_KEY=            # Encryption key used to serialize Discord IDs in OAuth redirect URLs

  ```

### 4. Database Initialization

  1. Log in to your Supabase Dashboard.

  2. Go to the SQL Editor.

  3. Open the file `supabase_schema.txt` located in the root of this repository.

  4. Copy the contents and run the query in Supabase to set up the required tables and RPC functions.

### 5. Running the Bot

  You will need to run the components in separate terminal windows (make sure your virtual environment is activated in each):

  Terminal 1: The Discord Bot
  ```bash
  python auth.py
  ```
  Terminal 2: The Web Server (OAuth)
  ```bash
  python web.py
  ```
  Terminal 3: The Background Sync (Optional) Only run this if you need to test live PP updates.
  ```bash
  python supabase_sync.py
  ```
