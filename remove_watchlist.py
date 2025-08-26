#!/usr/bin/python3
"""
Remove an item from Plex Watchlist.

Behavior
- Movies: removes the movie itself.
- Episodes: removes the parent show.
- Tries Plex Discover actions API first, then falls back to the item API.

Args (from Tautulli):
  --rating_key "{rating_key}" --media_type "{media_type}" --title "{title}" --username "{username}" \
  --baseurl "http://YOUR_PLEX_IP:32400" --token "PLEX_TOKEN" \
  [--account_token "PLEX_ACCOUNT_TOKEN"] [--only_username "yourname"] [--dry_run 1] [--debug 1]
"""

import sys
import argparse
import urllib.parse
import urllib.request
import urllib.error
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount

# Only use the official provider host
PROVIDER_HOST = "https://discover.provider.plex.tv"

def eprint(*a, **k): print(*a, file=sys.stderr, **k)

def parse_args():
    ap = argparse.ArgumentParser(description="Remove items from Plex Watchlist via Discover API.")
    # From Tautulli
    ap.add_argument("--rating_key", required=True, help="Plex ratingKey (library item key)")
    ap.add_argument("--media_type", required=True, help="movie | episode | show")
    ap.add_argument("--title", default="", help="Human-readable title")
    ap.add_argument("--username", default="", help="Plex username from Tautulli")
    # Connection / behavior
    ap.add_argument("--baseurl", required=True, help="e.g. http://YOUR_PLEX_IP:32400")
    ap.add_argument("--token", required=True, help="Server token (or account token)")
    ap.add_argument("--account_token", default="", help="(Optional) Account token for watchlist ops")
    ap.add_argument("--only_username", default="", help="If set, only act for this username")
    ap.add_argument("--dry_run", type=int, default=0, help="1 = log only, do not remove")
    ap.add_argument("--debug", type=int, default=0, help="1 = extra diagnostics")
    args, _ = ap.parse_known_args()
    return args

def get_account_username_if_possible(token):
    try:
        acc = MyPlexAccount(token=token)
        return getattr(acc, "username", None)
    except Exception:
        return None

def guid_variants_and_raw_id(item):
    """
    Collect GUIDs; derive raw id (tail of plex://{movie|show}/<id>) for Discover remove.
    """
    variants, raw_id = [], None
    primary = getattr(item, "guid", None)
    if primary:
        s = str(primary)
        variants.append(s)
        if s.startswith("plex://"):
            try:
                raw_id = s.rsplit("/", 1)[1]
            except Exception:
                raw_id = None
    for g in getattr(item, "guids", []) or []:
        val = getattr(g, "id", None) or getattr(g, "guid", None) or str(g)
        if val and str(val) not in variants:
            variants.append(str(val))
    plex_first = [g for g in variants if str(g).startswith("plex://")]
    others = [g for g in variants if not str(g).startswith("plex://")]
    variants = plex_first + others
    if raw_id is None:
        for g in variants:
            if str(g).startswith("plex://"):
                try:
                    raw_id = str(g).rsplit("/", 1)[1]
                    break
                except Exception:
                    pass
    return variants, raw_id

def build_request(url, method, headers, params_in_query=None, params_in_body=None):
    if params_in_query:
        parsed = urllib.parse.urlsplit(url)
        qs = urllib.parse.urlencode(params_in_query)
        url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, qs, parsed.fragment))
    body = urllib.parse.urlencode(params_in_body).encode("utf-8") if params_in_body else None
    req = urllib.request.Request(url, data=body, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    return req

def provider_remove(account_token, guid_candidates, raw_id, debug=False):
    """
    Try Discover actions API (PUT + ratingKey). Returns True if removed.
    """
    if not account_token or not raw_id:
        return False
    headers = {
        "X-Plex-Token": account_token,
        "Accept": "application/json",
        "X-Plex-Product": "TautulliScript",
        "X-Plex-Version": "1.0",
        "X-Plex-Client-Identifier": "tautulli-script",
    }

    base = f"{PROVIDER_HOST}/actions/removeFromWatchlist"
    tries = [
        ("PUT", base, {"ratingKey": raw_id}, None),
        ("PUT", base, None, {"ratingKey": raw_id}),
    ]
    for g in (guid_candidates or []):
        tries.append(("PUT", base, {"guid": g}, None))
        tries.append(("PUT", base, None, {"guid": g}))

    for method, url, q_params, b_params in tries:
        try:
            req = build_request(url, method, headers, q_params, b_params)
            with urllib.request.urlopen(req, timeout=10) as resp:
                code = getattr(resp, "status", 200)
            if debug:
                where = f"query:{q_params}" if q_params else f"body:{b_params}"
                eprint(f"[debug] {method} {url} ({where}) -> {code}")
            if code in (200, 204):
                return True
        except urllib.error.HTTPError as he:
            if debug:
                where = f"query:{q_params}" if q_params else f"body:{b_params}"
                eprint(f"[debug] {method} {url} ({where}) -> {he.code}")
            if he.code in (401, 403):
                return False
            continue
        except Exception as e:
            if debug:
                eprint(f"[debug] provider call failed: {e}")
            continue
    return False

def main():
    args = parse_args()

    # Act only for a specific username if requested
    if args.only_username and args.username and args.username != args.only_username:
        print(f"Skip: username '{args.username}' != only_username '{args.only_username}'")
        return 0

    acct_token = (args.account_token or args.token).strip()

    if args.debug:
        uname = get_account_username_if_possible(acct_token)
        if uname:
            eprint(f"[debug] acting_as account='{uname}'")

    # Connect to Plex to resolve show/movie and get GUIDs
    try:
        plex = PlexServer(args.baseurl, args.token)
    except Exception as e:
        eprint(f"ERROR: connecting to Plex failed: {e}")
        return 1

    media_type = (args.media_type or "").lower()
    try:
        rating_key = int(args.rating_key)
    except Exception:
        eprint("ERROR: rating_key must be an integer")
        return 1

    try:
        if media_type == "movie":
            item = plex.fetchItem(rating_key)
            target_desc = f"Movie: {item.title}"
        elif media_type in ("episode", "show"):
            ep_or_show = plex.fetchItem(rating_key)
            if getattr(ep_or_show, "type", "") == "episode":
                try:
                    item = ep_or_show.show()
                except Exception as e:
                    eprint(f"Skip: could not resolve parent show from episode ({e})")
                    return 0
            else:
                item = ep_or_show
            target_desc = f"Show: {getattr(item, 'title', args.title or 'Unknown')}"
        else:
            print(f"Skip: unsupported media_type '{args.media_type}'")
            return 0
    except Exception as e:
        eprint(f"ERROR: fetchItem({rating_key}) failed: {e}")
        return 1

    guid_list, raw_id = guid_variants_and_raw_id(item)
    if args.debug:
        eprint(f"[debug] acting on '{getattr(item,'title',None)}' type='{getattr(item,'type',None)}'")
        eprint(f"[debug] guid_primary='{getattr(item,'guid',None)}' guid_variants={guid_list} raw_id={raw_id}")

    if args.dry_run == 1:
        print(f"DRY RUN: would remove from Watchlist → {target_desc}")
        return 0

    # 1) Discover provider (preferred)
    if raw_id and provider_remove(acct_token, guid_list, raw_id, debug=bool(args.debug)):
        print(f"Removed from Watchlist (discover): {target_desc}")
        return 0

    # 2) Fallback: item API
    try:
        item.removeFromWatchlist()
        print(f"Removed from Watchlist (item API): {target_desc} (rating_key={rating_key})")
        return 0
    except Exception as e:
        if "404" in str(e) or "Not Found" in str(e):
            print(f"Already not on Watchlist (404 after all tries): {target_desc}")
            return 0
        eprint(f"ERROR: removeFromWatchlist failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
