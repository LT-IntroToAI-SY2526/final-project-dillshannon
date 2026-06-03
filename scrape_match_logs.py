import json
import requests
from bs4 import BeautifulSoup


def load_db(path="epl_stats.json"):
    with open(path, "r") as f:
        return json.load(f)


def save_db(db, path="epl_stats.json"):
    with open(path, "w") as f:
        json.dump(db, f, indent=4)


def get_player_match_log(player_id, player_name):
    # FBref URL format:
    # https://fbref.com/en/players/<ID>/<Name>-Match-Logs
    safe_name = player_name.replace(" ", "-")
    url = f"https://fbref.com/en/players/{player_id}/{safe_name}-Match-Logs"


    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")


    table = soup.find("table", id="matchlogs_all")
    if not table:
        return []


    rows = table.find("tbody").find_all("tr")
    match_log = []


    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue


        match = cells[4].text.strip()
        goals = int(cells[7].text or 0)
        assists = int(cells[8].text or 0)
        yellow = int(cells[10].text or 0)
        red = int(cells[11].text or 0)


        match_log.append({
            "match": match,
            "goals": goals,
            "assists": assists,
            "yellow": yellow,
            "red": red
        })


    return match_log


def build_event_list(match_log):
    events = []
    goal_count = assist_count = yellow_count = red_count = 0


    for game in match_log:
        for _ in range(game["goals"]):
            goal_count += 1
            events.append({
                "type": "goal",
                "match": game["match"],
                "index": goal_count
            })


        for _ in range(game["assists"]):
            assist_count += 1
            events.append({
                "type": "assist",
                "match": game["match"],
                "index": assist_count
            })


        for _ in range(game["yellow"]):
            yellow_count += 1
            events.append({
                "type": "yellow",
                "match": game["match"],
                "index": yellow_count
            })


        for _ in range(game["red"]):
            red_count += 1
            events.append({
                "type": "red",
                "match": game["match"],
                "index": red_count
            })


    return events


def scrape_all_players():
    print("FILE CONTENTS:", open("epl_stats.json").read())
    db = load_db()


    for name, pdata in db["players"].items():
        print(f"Scraping {name}...")


        player_id = pdata["id"]
        match_log = get_player_match_log(player_id, name)


        # Fill totals
        total_goals = sum(g["goals"] for g in match_log)
        total_assists = sum(g["assists"] for g in match_log)
        total_yellow = sum(g["yellow"] for g in match_log)
        total_red = sum(g["red"] for g in match_log)


        db["players"][name]["goals"] = total_goals
        db["players"][name]["assists"] = total_assists
        db["players"][name]["yellow_cards"] = total_yellow
        db["players"][name]["red_cards"] = total_red


        # Build event list
        db["players"][name]["events"] = build_event_list(match_log)


    save_db(db)
    print("Scraping complete — database updated!")


if __name__ == "__main__":
    scrape_all_players()


