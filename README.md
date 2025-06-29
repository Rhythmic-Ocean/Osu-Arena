# 🌀 rt4d Discord Bot

> [🌐 Website](https://rt4d-production.up.railway.app) | [💬 Join the Discord](https://discord.com/invite/GBsNU5hCQy)

**rt4d (Race to 4 Digits)** is a custom-built, real-time Discord bot designed for the **osu! community** at rt4d. It manages league sessions, rivalries, challenges, player verification, and rank syncing for a competitive community racing to reach 4-digit osu! global rank and beyond.

---

## ✨ Features

- 🔗 **osu! Account Linking** – Secure OAuth2-based account verification via website.
- 📊 **League System** – Automatically assigns users into leagues (Bronze → Master) based on osu! rank.
- ⚔️ **Rivalry & Challenge System** – Issue & manage direct 1v1 challenges with real-time updates.
- 🕒 **Live PP & Rank Updates** – Every player’s rank & pp is updated constantly in the database.
- 🔁 **Session Resets** – Admins can restart sessions to reassign league brackets.
- 📣 **Winner Announcements** – Rivalry winners are automatically detected and announced.
- ⚡ **Asynchronous Architecture** – Uses `asyncio` and parallel modules for optimal performance.
- 🌐 **OAuth Landing Page** – Hosted with Railway to handle account linking & redirection.

---

## 🧠 Commands

- 🆘 `!help`  
  Shows all available commands.

- 🔗 `!link`  
  Link your osu! account securely via OAuth2.  
  _(All users registered before June 18, 2025, 22:50 CDT were linked manually.)_

- 📊 `!show [league]`  
  View current standings in a league.  
  Examples:
  - `!show Bronze`
  - `!show Rivals`
  - `!show` (to list valid leagues)

- ⚔️ `!challenge @user <pp>`  
  Challenge a rival in your league.
  - PP must be 250–750  
  - Max 3 active challenges  
  - You may not challenge the same user twice a day

- ❌ `!revoke_challenge @user`  
  Cancel a pending challenge (before acceptance).

- 🛠️ `!session_restart`  
  **Admin-only** – Reassigns all users to leagues based on updated ranks.

---

## 🗂️ Project Structure

### 🔧 Main Modules (in root)

- `auth.py` – **Main bot entrypoint**, handles bot startup, event handling, and async execution  
- `core_v2.py` – Core **utility logic** behind all commands (DB ops, user logic, challenge logic)  
- `monitoring.py` – Async process that **monitors ongoing rivalries** and announces winners  
- `supaabse.py` – Separate process to **poll and sync player data (pp, ranks)** to Supabase  
- `web.py` – Flask app handling **OAuth2 flow**, callback routing, and token handling  
- `core_web.py` – Web-specific helpers used by `web.py`

### 💬 Commands Folder

- `commands/` – Contains all bot `@bot.command()` implementations  
  - Relies on helper functions in `core_v2.py`

---

## 🧱 Tech Stack

- **Python 3.12+**
- **[Discord.py](https://discordpy.readthedocs.io/en/stable/)** – Discord bot framework
- **[Supabase](https://supabase.com)** – Realtime Postgres database
- **[Railway](https://railway.app)** – Cloud hosting (used for all deployments)
- **[Flask](https://flask.palletsprojects.com/)** – Handles OAuth2 web flow
- **[osu.py](https://github.com/Sheppsu/osu.py)** – Python wrapper for the osu! API
- **[asyncio](https://docs.python.org/3/library/asyncio.html)** – Async tasks, loops, polling
- **osu! API v2** – For player stats, rank, and pp data

---

## 🛰️ Deployment Overview

> All major modules are deployed separately for scalability:

| Component      | Role                                           | Deployment        |
|----------------|------------------------------------------------|-------------------|
| `auth.py`      | Main Discord bot runtime                       | Railway (Bot Host)|
| `web.py`       | OAuth2 account linking + redirect handling     | Railway (Web App) |
| `supaabse.py`  | PP/Rank sync for all tracked users             | Railway (Worker)  |

---

## 🚀 Local Setup

### 📦 Prerequisites

- Python 3.12+
- Supabase project set up
- A Discord bot + osu! API credentials

### 🔐 .env File

Create a `sec.env` file with the following variables:

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token               # Main Discord bot token

# osu! API - Web + OAuth
AUTH_ID=your_osu_client_id                         # For OAuth (web)
AUTH_TOKEN=your_osu_client_secret                  # For OAuth (web)

# osu! API - Supaabse background sync
OSU_CLIENT2_ID=your_other_osu_client_id            # For supaabse.py (runs continuously)
OSU_CLIENT2_SECRET=your_other_osu_client_secret

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key        # Use service key for full access

# Web/OAuth
FLASK_SECKEY=your_flask_secret_key                 # Flask session encryption
SEC_KEY=your_discord_encryption_secret             # Used to securely encrypt Discord usernames/IDs (min 10 chars recommended)
```

▶️ Running Locally

pip install -r requirements.txt
python auth.py       # to start the bot
python web.py        # to start OAuth web app
python supaabse.py   # to sync pp/rank with Supabase