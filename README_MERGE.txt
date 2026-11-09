╔══════════════════════════════════════════════════════════════╗
║       SHOWN X PANEL v3.0 ULTRA — MERGE + RUN GUIDE          ║
╚══════════════════════════════════════════════════════════════╝

─── STEP 1: MERGE THE TWO PARTS ────────────────────────────────

Option A — Manual:
  1. Open shownXpannel_v3_part1_fixed.py
  2. Delete the last 5 lines (the # PART 1 ENDS HERE block)
  3. Open shownXpannel_v3_part2_fixed.py
  4. Delete the first 8 lines (#!/usr/bin/env + docstring block)
  5. Paste part2 content at the end of part1
  6. Save as shownXpannel_v3_final.py

Option B — Command line (Linux/Mac):
  head -n -5 shownXpannel_v3_part1_fixed.py > shownXpannel_v3_final.py
  tail -n +9 shownXpannel_v3_part2_fixed.py >> shownXpannel_v3_final.py

─── STEP 2: SET YOUR BOT TOKEN ─────────────────────────────────

Option A — Edit the file:
  Open shownXpannel_v3_final.py
  Line 71: BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
  Replace with your actual token from @BotFather

Option B — Environment variable (recommended for hosting):
  export BOT_TOKEN=your_token_here
  (or put in .env file, see .env.example)

─── STEP 3: INSTALL DEPENDENCIES ───────────────────────────────

  pip install -r requirements.txt

─── STEP 4: RUN ─────────────────────────────────────────────────

  python shownXpannel_v3_final.py

─── HOSTING (Render / Railway / VPS) ───────────────────────────

  Start command:  python shownXpannel_v3_final.py
  Health check:   http://your-url/health  (port 10000)
  Set env vars:   BOT_TOKEN, OWNER_ID, etc. in dashboard

─── ADMIN COMMANDS ──────────────────────────────────────────────

  /grant USER_ID       — Grant panel access
  /revoke USER_ID      — Revoke access
  /adddb NAME URL      — Add Firebase DB
  /removedb NAME       — Remove a DB
  /backup              — Send backup to your DM
  /monitor             — Toggle live OTP alerts
  /health              — Run Firebase health check
  /stats               — View dashboard stats
  /admin               — Open admin panel menu

─── USER COMMANDS ───────────────────────────────────────────────

  /start               — Welcome screen
  /panel               — Browse databases
  /status              — System status
  /hub                 — Your number history
  /help                — Help screen

─── FILES ───────────────────────────────────────────────────────

  shownxpanel.db       — SQLite database (auto-created on first run)
  bot_database.json    — OLD file: auto-migrated on first run then renamed
                         to bot_database.json.migrated

╚══════════════════════════════════════════════════════════════╝
