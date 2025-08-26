# Plex Watchlist Cleaner

Keep your Plex Watchlist tidy with two small utilities:
- **Tautulli integration**: removes a finished movie (or the parent show of a stopped episode) when playback stops.
- **Batch cleanup**: scans your Watchlist and removes anything watched or started (configurable).

Requires Python 3.9+ and [`plexapi`](https://github.com/pkkid/python-plexapi) 4.17.1 or higher

## Tautulli Setup (Playback Stop → remove_watchlist.py)

**When it runs:**  
- Triggered by **Tautulli** on *Playback Stop*.

**What it does functionally:**  
- Looks at the item you just stopped watching.  
- If it’s a **movie**, that movie is removed from your Plex Watchlist.  
- If it’s an **episode**, the script removes the **entire parent show** from the Watchlist.  <- optional
- Decides whether to act based on the user (supports `--only_username`).  
- Communicates with Plex Discover API to remove the item; if that fails, uses Plex’s own API as fallback.  

**Why this matters:**  
- Prevents movies or shows you’ve already started from lingering in your Watchlist.  
- Works instantly at the point of playback, keeping things clean without manual steps.  

---

## Installation

```bash
pip install plexapi
```

---

1. Save the script somewhere Tautulli can access it, e.g. `/opt/scripts/remove_watchlist.py`.  
2. In Tautulli, go to **Settings → Notification Agents → Add → Script**.  
3. Under **Triggers**, enable **Playback Stop**.  
4. Under **Conditions**, configure:  

   **Condition Group A (OR):**
   - Media Type **is** `movie`  
   - Media Type **is** `episode`  

   **Condition Group B (AND):**
   - Username **is** `YourPlexUser` *(optional: only if you want this limited to one account)*  
   - Progress (%) **is greater than or equal to** `1`  
     - Use `>= 1` → remove items as soon as playback has started.  
     - Use `>= 90` (or higher) → only remove items that are almost finished.  

   *(Group A and Group B are combined with **AND** logic.)*  

5. Under **Script Arguments**, paste (adjust IP and tokens):  

```
--rating_key "{rating_key}" --media_type "{media_type}" --title "{title}" --username "{username}" --baseurl "http://YOUR_PLEX_IP:32400" --token "PLEX_TOKEN" --account_token "PLEX_ACCOUNT_TOKEN"
```

### Optional Script Flags
- `--only_username "YourPlexUser"` → double-check safeguard to restrict to one user  
- `--dry_run 1` → test mode, logs actions without removing  
- `--debug 1` → verbose output  

### Functional Outcome
- **Movie stopped** → movie is removed from Watchlist if conditions match.  
- **Episode stopped** → parent **show** is removed from Watchlist if conditions match.  
- The **Progress %** condition controls whether items are removed after *any* playback or only once they’re nearly finished.  

---
## Batch Cleanup (backlog_watchlist.py) - doesnt require TAUTULLI

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

1. Edit the `CONFIG` block in the file:
   - `BASEURL`: e.g. `http://YOUR_PLEX_IP:32400`
   - `TOKEN`: server token
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

### Functional Outcome
- **Movies** → removed once marked watched.  
- **Shows** → removal depends on `SHOW_REMOVE` setting:  
  - `"started"` → remove once any episode is watched.  
  - `"completed"` → remove only when the whole show is watched.  
- Cleans your entire Watchlist in one go, great for nightly jobs.  

---

## Notes & Troubleshooting

- 401/403 from Discover API → account token invalid or wrong user.  If you get authentication errors the PLEX_ACCOUNT_TOKEN by PLEX_SERVER_TOKEN AND the PLEX_ACCOUNT_TOKEN.
- 404 on removal → usually already off the Watchlist.  
- For episodes, the script removes the **parent show**.  
- Start with `--dry_run 1` to verify behavior.  

---

## How to Get Your Plex Account Token

Some actions (like removing items from the Watchlist) require your **Plex account token**.  

### From a Web Browser
1. Log in to [https://app.plex.tv](https://app.plex.tv).  
2. Open the browser’s developer tools (**F12** or **Ctrl+Shift+I**).  
3. Go to the **Network** tab and refresh the page.  
4. Click any request to `plex.tv` or `discover.provider.plex.tv`.  
5. Look for a header or query parameter called:  
   ```
   X-Plex-Token=xxxxxxxxxxxxxxxxxxxx
   ```
   That value is your account token.

⚠️ **Important**
- The token is tied to your Plex account. Keep it private (don’t share or publish).  
- If you rotate or remove devices from your Plex account, tokens may change — you’ll need to grab a new one.  

---
