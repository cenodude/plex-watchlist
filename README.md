# Plex Watchlist Cleaner

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
