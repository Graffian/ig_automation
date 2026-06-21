# Instagram Automation Tracker

Track posts, comments, followers, and following for any Instagram account using `instagrapi`.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 3. Run tracking (generates CSV reports automatically)
python main.py track

# 4. See what changed
python main.py summary
python main.py unfollowers
```

## Features

- **Posts** — tracks captions, like count, comment count over time
- **Comments** — records who commented and what they said
- **Followers** — detects new followers and unfollowers
- **Following** — detects new follows and unfollows
- **Parallel tracking** — tracks multiple accounts simultaneously
- **CSV Reports** — auto-generated reports in `reports/` folder after each run
- **Scheduled runs** — use Task Scheduler with included scripts
- **History** — all data stored in SQLite for trend analysis
- **Continuous mode** — runs on a timer and reports changes

## Setup

```bash
pip install -r requirements.txt
```

Edit `config.json`:

```json
{
    "username": "your_instagram_login",
    "password": "your_instagram_password",
    "track_interval_minutes": 30,
    "target_accounts": ["account_to_track"]
}
```

## Usage

```bash

# One-time tracking (parallel, CSV reports auto-generated)
python main.py track

# Track without CSV reports
python main.py track --no-report

# Track specific accounts (overrides config)
python main.py track -a account1 account2

# Continuous tracking every N minutes
python main.py track -i 60

# Show stored summary
python main.py summary

# Show unfollowers
python main.py unfollowers
```

## CSV Reports

After each `track` run, CSV files are generated in `reports/`:

| File | Contents |
|---|---|
| `{account}_followers.csv` | All followers (active + unfollowed) |
| `{account}_following.csv` | All following (active + unfollowed) |
| `{account}_posts.csv` | Post stats and captions |
| `{account}_comments.csv` | All recorded comments |

## Scheduled Runs (Windows)

### Option 1: Task Scheduler (recommended)

1. Open **Task Scheduler** → **Create Basic Task**
2. Trigger: Daily, repeat every 30 minutes
3. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "D:\ig_automation\run_tracker.ps1"`
   - Start in: `D:\ig_automation`

### Option 2: Batch file

Schedule `run_tracker.bat` the same way. Logs go to `logs/` folder.

## Data

All data is stored locally in `instagram_data.db` (SQLite). Tables:

- `posts` — per-post stats and captions
- `comments` — comment threads per post
- `followers` — follower history with active/inactive status
- `following` — following history with active/inactive status
- `tracking_snapshots` — numeric snapshots for charts

The database auto-creates on first run. Safe to delete anytime — it'll be recreated.

## .gitignore

A `.gitignore` is included. It prevents committing:
- `instagram_data.db` — tracking data
- `config.json` — your Instagram password
- `reports/` — CSV exports
- `logs/` — scheduled run logs
- `__pycache__/` — Python cache

## Notes

- Instagram may rate-limit or challenge unusual activity. Use realistic intervals (30+ min).

