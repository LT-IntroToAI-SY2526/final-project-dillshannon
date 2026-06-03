"""
epl_bot.py  —  EPL Statistics Chatbot
Powered by the official Fantasy Premier League (FPL) API.
  - No API key needed
  - No scraping
  - No JSON file to maintain
  - Covers EVERY Premier League player
  - Per-gameweek match history for nth-event queries


HOW TO RUN:
  pip install requests
  python epl_bot.py


EXAMPLE QUERIES:
  who has the most goals
  who has the most assists
  who has the most yellow cards
  who has the most red cards
  how many goals does _____ have
  how many assists does ______ have
  how many yellow cards does _______ have
  how many red cards does __________ have
  what team does ________ play for
  what game did _______ score his 5th goal
  what game did __________ get his 3rd assist
  what game did ______ get his 1st yellow card
  what game did ______ get his 1st red card
  bye
"""


import re
import time
import requests
from typing import List, Callable, Tuple, Any, Optional


# ─────────────────────────────────────────────────────────────
# match()  —  identical interface to the original assignment
# ─────────────────────────────────────────────────────────────


def match(pattern: List[str], source: List[str]) -> Optional[List[str]]:
    """
    Pattern-match with % as a wildcard absorbing one or more tokens.
    Returns the tokens matched by % if pattern fits source, else None.
    """
    if "%" not in pattern:
        return source if source == pattern else None


    pivot = pattern.index("%")
    pre   = pattern[:pivot]
    post  = pattern[pivot + 1:]


    if source[:len(pre)] != pre:
        return None
    if post and source[-len(post):] != post:
        return None


    start = len(pre)
    end   = len(source) - len(post) if post else len(source)


    if start > end:
        return None


    return source[start:end]




# ─────────────────────────────────────────────────────────────
# FPL API  —  three endpoints, cached after first fetch
# ─────────────────────────────────────────────────────────────


BASE = "https://fantasy.premierleague.com/api"
HEADERS = {"User-Agent": "epl-chatbot-student/1.0"}


_cache: dict = {}




def _get(url: str) -> dict:
    """GET a URL with simple retry logic."""
    for attempt in range(5):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 5))
                print(f"  [rate limited — waiting {wait}s...]")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == 4:
                raise ConnectionError(f"API request failed: {e}")
            time.sleep(2)
    raise ConnectionError("API request failed after 5 attempts")




def _bootstrap() -> dict:
    """
    Fetch bootstrap-static once and cache it.
    Contains every player's season totals + team list.
    """
    if "bootstrap" not in _cache:
        print("  [loading EPL player data from FPL API...]")
        _cache["bootstrap"] = _get(f"{BASE}/bootstrap-static/")
    return _cache["bootstrap"]




def _teams() -> dict:
    """Return {team_id: team_name} mapping."""
    if "teams" not in _cache:
        data = _bootstrap()
        _cache["teams"] = {t["id"]: t["name"] for t in data["teams"]}
    return _cache["teams"]




def _all_players() -> List[dict]:
    """
    Return the full list of player dicts from bootstrap, each enriched with
    'full_name' and 'team_name'.
    """
    if "players" not in _cache:
        data   = _bootstrap()
        teams  = _teams()
        players = []
        for p in data["elements"]:
            p = dict(p)
            p["full_name"]  = f"{p['first_name']} {p['second_name']}"
            p["team_name"]  = teams.get(p["team"], "Unknown")
            players.append(p)
        _cache["players"] = players
    return _cache["players"]




def _element_summary(player_id: int) -> dict:
    """
    Fetch per-gameweek history for a player.
    Each entry in ['history'] has: round, opponent_team, goals_scored,
    assists, yellow_cards, red_cards, fixture, was_home, kickoff_time.
    """
    key = f"summary_{player_id}"
    if key not in _cache:
        _cache[key] = _get(f"{BASE}/element-summary/{player_id}/")
    return _cache[key]




def _fixtures_map() -> dict:
    """Return {fixture_id: 'Home Team vs Away Team'} for match labels."""
    if "fixtures_map" not in _cache:
        print("  [loading fixture data from FPL API...]")
        fixtures = _get(f"{BASE}/fixtures/")
        teams    = _teams()
        fmap     = {}
        for f in fixtures:
            home = teams.get(f["team_h"], "?")
            away = teams.get(f["team_a"], "?")
            fmap[f["id"]] = f"{home} vs {away}"
        _cache["fixtures_map"] = fmap
    return _cache["fixtures_map"]




# ─────────────────────────────────────────────────────────────
# Player lookup helpers
# ─────────────────────────────────────────────────────────────


def _find_player(name_tokens: List[str]) -> dict:
    """
    Case-insensitive fuzzy search across all EPL players.
    Returns the player dict or raises LookupError.
    """
    query = " ".join(name_tokens).lower()
    players = _all_players()


    # Exact full-name match
    for p in players:
        if p["full_name"].lower() == query:
            return p


    # All query words appear somewhere in the full name
    words = query.split()
    matches = [p for p in players if all(w in p["full_name"].lower() for w in words)]


    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(p["full_name"] for p in matches[:5])
        raise LookupError(f"Ambiguous — did you mean one of: {names}?")


    raise LookupError(f"Player '{query}' not found. Check the spelling.")




def _ordinal_to_int(token: str) -> int:
    return int(re.sub(r"(st|nd|rd|th)$", "", token.lower().strip()))




def _to_ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return {1: f"{n}st", 2: f"{n}nd", 3: f"{n}rd"}.get(n % 10, f"{n}th")




def _match_label(gw_entry: dict) -> str:
    """Human-readable match label from a gameweek history entry."""
    fmap     = _fixtures_map()
    fixture  = gw_entry.get("fixture")
    label    = fmap.get(fixture, f"Gameweek {gw_entry.get('round', '?')}")
    gw       = gw_entry.get("round", "?")
    was_home = gw_entry.get("was_home", True)
    kickoff  = gw_entry.get("kickoff_time", "")[:10]  # YYYY-MM-DD
    side     = "H" if was_home else "A"
    return f"GW{gw} ({kickoff}) {label} [{side}]"




# ─────────────────────────────────────────────────────────────
# Action functions  (same style as original assignment)
# ─────────────────────────────────────────────────────────────


# ── Season leaders ───────────────────────────────────────────


def _leader(stat_key: str, label: str) -> List[str]:
    players = _all_players()
    if not players:
        raise LookupError("No player data loaded.")
    best = max(players, key=lambda p: p.get(stat_key, 0))
    val  = best.get(stat_key, 0)
    return [f"{best['full_name']} ({best['team_name']}) leads with {val} {label}"]




def most_goals(matches: List[str]) -> List[str]:
    return _leader("goals_scored", "goals")


def most_assists(matches: List[str]) -> List[str]:
    return _leader("assists", "assists")


def most_yellow_cards(matches: List[str]) -> List[str]:
    return _leader("yellow_cards", "yellow cards")


def most_red_cards(matches: List[str]) -> List[str]:
    return _leader("red_cards", "red cards")




# ── Player-specific stat totals ──────────────────────────────


def _player_stat(name_tokens: List[str], stat_key: str, label: str) -> List[str]:
    p   = _find_player(name_tokens)
    val = p.get(stat_key, 0)
    return [f"{p['full_name']} ({p['team_name']}): {val} {label}"]


def player_goals(matches: List[str]) -> List[str]:
    return _player_stat(matches, "goals_scored", "goals")


def player_assists(matches: List[str]) -> List[str]:
    return _player_stat(matches, "assists", "assists")


def player_yellow_cards(matches: List[str]) -> List[str]:
    return _player_stat(matches, "yellow_cards", "yellow cards")


def player_red_cards(matches: List[str]) -> List[str]:
    return _player_stat(matches, "red_cards", "red cards")


def player_team(matches: List[str]) -> List[str]:
    p = _find_player(matches)
    return [f"{p['full_name']} plays for {p['team_name']}"]




# ── Nth event queries ─────────────────────────────────────────


def _nth_event_dispatcher(tokens: List[str]) -> List[str]:
    """
    Parse: 'what game did <name> score/get his <N>th goal/assist/yellow card/red card'
    Uses per-gameweek history from the FPL element-summary endpoint.
    """
    sentence = " ".join(tokens)


    m = re.search(
        r"what game did (.+?) (?:score|get) (?:his|her|their) "
        r"(\d+(?:st|nd|rd|th)?)\s*(goal|assist|yellow card|red card)",
        sentence,
        re.IGNORECASE,
    )
    if not m:
        raise ValueError(
            "Couldn't parse — try: 'what game did [name] score his [N]th goal'"
        )


    name_tokens = m.group(1).strip().split()
    n           = _ordinal_to_int(m.group(2))
    event_word  = m.group(3).lower()


    # Map phrase → FPL history field
    field_map = {
        "goal":        "goals_scored",
        "assist":      "assists",
        "yellow card": "yellow_cards",
        "red card":    "red_cards",
    }
    field = field_map[event_word]


    # Label for output
    label_map = {
        "goals_scored": "goal",
        "assists":      "assist",
        "yellow_cards": "yellow card",
        "red_cards":    "red card",
    }
    label = label_map[field]


    # Find player
    player = _find_player(name_tokens)
    print(f"  [fetching match history for {player['full_name']}...]")
    summary  = _element_summary(player["id"])
    history  = summary.get("history", [])


    # Walk through gameweeks, expanding each event occurrence
    events = []
    for gw in history:
        count = gw.get(field, 0)
        for _ in range(count):
            events.append(gw)


    if not events:
        return [f"{player['full_name']} has no {label} events recorded this season."]


    if n < 1 or n > len(events):
        return [
            f"{player['full_name']} only has {len(events)} {label}(s) recorded; "
            f"you asked for number {n}."
        ]


    gw_entry = events[n - 1]
    match_str = _match_label(gw_entry)


    return [
        f"{player['full_name']}'s {_to_ordinal(n)} {label} was scored/recorded in: {match_str}"
    ]




def bye_action(dummy: List[str]) -> None:
    raise KeyboardInterrupt




# ─────────────────────────────────────────────────────────────
# Pattern–action list  (same style as original assignment)
# ─────────────────────────────────────────────────────────────


Pattern = List[str]
Action  = Callable[[List[str]], List[Any]]


pa_list: List[Tuple[Pattern, Action]] = [


    # ── Season leaders ──
    ("who has the most goals".split(),        most_goals),
    ("who scored the most goals".split(),     most_goals),
    ("who has the most assists".split(),      most_assists),
    ("who has the most yellow cards".split(), most_yellow_cards),
    ("who has the most red cards".split(),    most_red_cards),


    # ── Player-specific totals ──
    ("how many goals does % have".split(),        player_goals),
    ("how many assists does % have".split(),      player_assists),
    ("how many yellow cards does % have".split(), player_yellow_cards),
    ("how many red cards does % have".split(),    player_red_cards),
    ("what team does % play for".split(),         player_team),


    # ── bye ──
    (["bye"], bye_action),
]




# ─────────────────────────────────────────────────────────────
# Query engine  (same style as original assignment)
# ─────────────────────────────────────────────────────────────


def search_pa_list(src: List[str]) -> List[str]:
    sentence = " ".join(src)


    # Nth-event queries use a regex dispatcher (checked first)
    if sentence.startswith("what game did"):
        return _nth_event_dispatcher(src)


    # Standard pattern-action matching
    for pat, act in pa_list:
        mat = match(pat, src)
        if mat is not None:
            answer = act(mat)
            return answer if answer else ["No answer found"]


    return [
        "I don't understand. Try one of:\n"
        "  'who has the most goals'\n"
        "  'who has the most assists'\n"
        "  'who has the most yellow cards'\n"
        "  'who has the most red cards'\n"
        "  'how many goals does [player name] have'\n"
        "  'how many assists does [player name] have'\n"
        "  'how many yellow cards does [player name] have'\n"
        "  'how many red cards does [player name] have'\n"
        "  'what team does [player name] play for'\n"
        "  'what game did [player name] score his [N]th goal'\n"
        "  'what game did [player name] get his [N]th assist'\n"
        "  'what game did [player name] get his [N]th yellow card'\n"
        "  'what game did [player name] get his [N]th red card'"
    ]




def query_loop() -> None:
    print("=" * 55)
    print("  EPL 2024-25 Chatbot  (powered by FPL API)")
    print("=" * 55)
    print("  Live data — covers every Premier League player.")
    print("  First query loads player data (~1-2 seconds).\n")


    while True:
        try:
            print()
            raw = input("Your query? ").replace("?", "").strip().lower()
            if not raw:
                continue
            tokens  = raw.split()
            answers = search_pa_list(tokens)
            for ans in answers:
                print(" →", ans)


        except LookupError as e:
            print(f" [Not found] {e}")
        except ValueError as e:
            print(f" [Parse error] {e}")
        except ConnectionError as e:
            print(f" [Network error] {e}")
        except (KeyboardInterrupt, EOFError):
            break


    print("\nSo long!\n")




if __name__ == "__main__":
    query_loop()


