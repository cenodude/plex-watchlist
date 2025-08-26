#!/usr/bin/python3

# =========================
# ######## CONFIG #########
# =========================
CONFIG = {
    "BASEURL": "http://YOUR_PLEX_IP:32400",
    "TOKEN": "PLEX_TOKEN",
    "ACCOUNT_TOKEN": "PLEX_ACCOUNT_TOKEN",
    "TYPES": ["movie", "show"],
    "SHOW_REMOVE": "started",  # "started" or "completed"
    "DRY_RUN": 0,
    "LIMIT": 0,
    "DEBUG": 0,
}
# =========================
# #### END OF CONFIG ######
# =========================

import sys, json, urllib.parse, urllib.request, urllib.error
from typing import List, Optional, Tuple
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount

DISCOVER_HOST = "https://discover.provider.plex.tv"

def log(*a, **k): print(*a, **k)
def dlog(*a): 
    if CONFIG["DEBUG"]: print(*a)

def discover_get_watchlist(account_token: str, limit: int) -> list:
    headers = {
        "X-Plex-Token": account_token,
        "Accept": "application/json",
        "X-Plex-Product": "BacklogCleaner",
        "X-Plex-Version": "1.0",
        "X-Plex-Client-Identifier": "backlog-cleaner",
    }
    params = {"includeCollections": "1", "includeExternalMedia": "1"}
    if limit and limit > 0:
        params["X-Plex-Container-Start"] = "0"
        params["X-Plex-Container-Size"] = str(limit)

    url = f"{DISCOVER_HOST}/library/sections/watchlist/all?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        md = data.get("MediaContainer", {}).get("Metadata", []) or []
        dlog(f"[debug] watchlist items fetched: {len(md)} from {DISCOVER_HOST}")
        return md
    except Exception as e:
        raise RuntimeError(f"Failed to fetch watchlist: {e}")

def extract_guid_and_rawid(guid_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not guid_str:
        return None, None
    g = str(guid_str)
    raw_id = None
    if g.startswith("plex://") and "/" in g:
        try:
            raw_id = g.rsplit("/", 1)[1]
        except Exception:
            raw_id = None
    return g, raw_id

def guid_variants(item) -> List[str]:
    cands = []
    primary = getattr(item, "guid", None)
    if primary: cands.append(str(primary))
    for g in getattr(item, "guids", []) or []:
        val = getattr(g, "id", None) or getattr(g, "guid", None) or str(g)
        if val and str(val) not in cands:
            cands.append(str(val))
    plex_first = [x for x in cands if str(x).startswith("plex://")]
    others = [x for x in cands if not str(x).startswith("plex://")]
    return plex_first + others

def provider_remove(account_token: str, raw_id: str, guid_list: List[str]) -> bool:
    if not account_token or not raw_id:
        return False
    headers = {
        "X-Plex-Token": account_token,
        "Accept": "application/json",
        "X-Plex-Product": "BacklogCleaner",
        "X-Plex-Version": "1.0",
        "X-Plex-Client-Identifier": "backlog-cleaner",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    url = f"{DISCOVER_HOST}/actions/removeFromWatchlist"
    tries = [
        ("PUT", url, {"ratingKey": raw_id}, None),
        ("PUT", url, None, {"ratingKey": raw_id}),
    ]
    for g in (guid_list or []):
        tries.append(("PUT", url, {"guid": g}, None))
        tries.append(("PUT", url, None, {"guid": g}))

    for method, u, q, b in tries:
        try:
            if q:
                parsed = urllib.parse.urlsplit(u)
                qs = urllib.parse.urlencode(q)
                u = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, qs, parsed.fragment))
            data = urllib.parse.urlencode(b).encode("utf-8") if b else None
            req = urllib.request.Request(u, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=12) as resp:
                code = getattr(resp, "status", 200)
            dlog(f"[debug] {method} {u} -> {code}")
            if code in (200, 204):
                return True
        except urllib.error.HTTPError as he:
            dlog(f"[debug] {method} {u} -> {he.code}")
            if he.code in (401, 403):
                return False
            continue
        except Exception as e:
            dlog(f"[debug] provider call failed: {e}")
            continue
    return False

def find_local_item(plex: PlexServer, wl_title: str, wl_year: Optional[int], wl_type: str, wl_guid: Optional[str]):
    try:
        if wl_guid:
            results = plex.library.search(guid=wl_guid)
            if results:
                return results[0]
    except Exception as e:
        dlog(f"[debug] search by guid failed: {e}")

    libtype = "movie" if wl_type == "movie" else "show" if wl_type == "show" else None
    if not libtype:
        return None
    try:
        results = plex.library.search(title=wl_title, libtype=libtype)
    except Exception as e:
        dlog(f"[debug] title search failed: {e}")
        return None
    if not results:
        return None

    if wl_year:
        filtered = [r for r in results if str(getattr(r, "year", "")) == str(wl_year)]
        if filtered:
            results = filtered

    if wl_guid:
        for r in results:
            try:
                guids = [str(getattr(r, "guid", ""))] + [
                    str(getattr(g, "id", "") or getattr(g, "guid", "") or g)
                    for g in (getattr(r, "guids", []) or [])
                ]
                if wl_guid in guids:
                    return r
            except Exception:
                pass
    return results[0] if results else None

def is_movie_watched(item) -> bool:
    return bool(getattr(item, "isWatched", False) or getattr(item, "viewCount", 0) > 0)

def is_show_started(item) -> bool:
    return bool(getattr(item, "viewedLeafCount", 0) > 0)

def is_show_completed(item) -> bool:
    v = int(getattr(item, "viewedLeafCount", 0) or 0)
    t = int(getattr(item, "leafCount", 0) or 0)
    return t > 0 and v >= t

def remove_one(account_token: str, plex_item) -> bool:
    guid_list = guid_variants(plex_item)
    _, raw_id = extract_guid_and_rawid(str(getattr(plex_item, "guid", "")))
    if raw_id and provider_remove(account_token, raw_id, guid_list):
        return True
    try:
        plex_item.removeFromWatchlist()
        return True
    except Exception as e:
        dlog(f"[debug] item.removeFromWatchlist() failed: {e}")
        return False

def main():
    baseurl       = CONFIG["BASEURL"].strip()
    token         = CONFIG["TOKEN"].strip()
    account_token = (CONFIG["ACCOUNT_TOKEN"] or token).strip()
    types         = set([t.strip().lower() for t in CONFIG["TYPES"]])
    show_remove   = CONFIG["SHOW_REMOVE"]
    dry_run       = int(CONFIG["DRY_RUN"] or 0)
    limit         = int(CONFIG["LIMIT"] or 0)

    try:
        uname = MyPlexAccount(token=account_token).username
        dlog(f"[debug] acting_as account='{uname}'")
    except Exception:
        pass

    try:
        plex = PlexServer(baseurl, token)
    except Exception as e:
        log(f"ERROR: PlexServer connect failed: {e}")
        return 2

    try:
        wl = discover_get_watchlist(account_token, limit)
    except Exception as e:
        log(f"ERROR: failed to fetch watchlist: {e}")
        return 2

    want_movie = "movie" in types
    want_show  = "show"  in types

    removed = 0
    skipped = 0
    unmatched = 0

    for w in wl:
        wl_type = w.get("type")
        if wl_type not in ("movie", "show"):
            continue
        if (wl_type == "movie" and not want_movie) or (wl_type == "show" and not want_show):
            continue

        title = w.get("title") or w.get("originalTitle") or "Unknown"
        year = w.get("year")
        guid = w.get("guid")
        primary_guid, raw_id = extract_guid_and_rawid(guid)

        dlog(f"[debug] scanning: {wl_type} '{title}' ({year}) guid={primary_guid} raw={raw_id}")

        item = find_local_item(plex, title, year, wl_type, primary_guid)
        if not item:
            dlog(f"[debug] no local match → skip")
            unmatched += 1
            continue

        if wl_type == "movie":
            should_remove = is_movie_watched(item)
        else:
            should_remove = is_show_completed(item) if show_remove == "completed" else is_show_started(item)

        if not should_remove:
            dlog(f"[debug] not watched enough → skip")
            skipped += 1
            continue

        if dry_run:
            log(f"DRY RUN: would remove from Watchlist → {wl_type}: {title}")
            removed += 1
            continue

        ok = remove_one(account_token, item)
        if ok:
            log(f"Removed from Watchlist: {wl_type}: {title}")
            removed += 1
        else:
            log(f"FAILED to remove: {wl_type}: {title}")
            skipped += 1

    log(f"\nSummary: removed={removed} skipped={skipped} unmatched={unmatched} (total={len(wl)})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
