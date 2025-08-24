# Plex Watchlist Cleaner

# Functional Explanation

These scripts automate the management of your Plex Watchlist.  
They focus on removing items you’ve already consumed, so your Watchlist always stays relevant.

---

## `remove_watchlist.py` (real-time cleanup)

**When it runs:**  
- Triggered by **Tautulli** on *Playback Stop*.

**What it does functionally:**  
- Looks at the item you just stopped watching.  
- If it’s a **movie**, that movie is removed from your Plex Watchlist.  
- If it’s an **episode**, the script removes the **entire parent show** from the Watchlist.  
- Decides whether to act based on the user (supports `--only_username`).  
- Communicates with Plex Discover API to remove the item; if that fails, uses Plex’s own API as fallback.  

**Why this matters:**  
- Prevents movies or shows you’ve already started from lingering in your Watchlist.  
- Works instantly at the point of playback, keeping things clean without manual steps.  

---

## `backlog_watchlist.py` (scheduled cleanup)

**When it runs:**  
- Run manually or on a schedule (e.g., daily via cron).

**What it does functionally:**  
- Fetches your entire Plex Watchlist via Plex Discover.  
- For each item:  
  - **Movies:** If marked as watched, remove from Watchlist.  
  - **Shows:** Behavior depends on your setting:  
    - `started`: remove if you’ve watched at least one episode.  
    - `completed`: remove only if you’ve watched all episodes.  
- Matches items against your local Plex library before removal.  
- Attempts removal via Plex Discover API; falls back to Plex item API.  

**Why this matters:**  
- Provides bulk cleanup, so your Watchlist doesn’t accumulate old watched items.  
- Lets you define how aggressive cleanup should be (started vs. completed).  
- Great for scheduled maintenance (e.g., run nightly).  

---

## Combined Use

- **remove_watchlist.py** → immediate cleanup as you finish watching.  
- **backlog_watchlist.py** → safety net for anything left behind.  

Together, they ensure your Plex Watchlist always shows *only unwatched and relevant content*.  


Keep your Plex Watchlist tidy with two small utilities:
- **Tautulli integration**: removes a finished movie (or the parent show of a stopped episode) when playback stops.
- **Batch cleanup**: scans your Watchlist and removes anything watched or started (configurable).

Requires Python 3.9+ and [`plexapi`](https://github.com/pkkid/python-plexapi).

---

## Installation

```bash
pip install plexapi
```

---

## Tautulli Setup (Playback Stop → remove_watchlist.py)

1. Put the script somewhere Tautulli can execute it, e.g. `/opt/scripts/remove_watchlist.py`.
2. Tautulli → **Settings → Notification Agents → Add → Script**.
3. Set **Trigger** to **Playback Stop**.
4. Paste the args below into **Script Arguments** (adjust IP/tokens):

```
--rating_key "{rating_key}" --media_type "{media_type}" --title "{title}" --username "{username}" --baseurl "http://YOUR_PLEX_IP:32400" --token "PLEX_TOKEN" --account_token "PLEX_ACCOUNT_TOKEN"
```

**Optional flags**
- `--only_username "YourPlexUser"` — only act for this user  
- `--dry_run 1` — log only, no changes  
- `--debug 1` — verbose logging  

---

## Batch Cleanup (backlog_watchlist.py)

1. Edit the `CONFIG` block in the file:
   - `BASEURL`: e.g. `http://YOUR_PLEX_IP:32400`
   - `TOKEN`: server token or if that doesnt work use account token!
   - `ACCOUNT_TOKEN`: account token (ensures the correct user’s Watchlist)
   - `TYPES`: `["movie", "show"]`
   - `SHOW_REMOVE`: `"started"` or `"completed"`
   - `DRY_RUN`: `1` (test) or `0` (apply)

2. Run it:
```bash
python3 backlog_watchlist.py
```

3. Cron example (daily at 03:30):
```cron
30 3 * * * /usr/bin/python3 /opt/scripts/backlog_watchlist.py >> /var/log/plex_watchlist.log 2>&1
```

---

## Notes & Troubleshooting

- 401/403 from Discover API → account token invalid or wrong user.
- 404 on removal → usually already off the Watchlist.
- For episodes, the script removes the **parent show**.
- Start with `--dry_run 1` to verify behavior.

---

## Scripts

### `remove_watchlist.py`

```python
# (script content from remove_watchlist.py goes here)
```

---

### `backlog_watchlist.py`

```python
# (script content from backlog_watchlist.py goes here)
```
