import json
import requests
from bs4 import BeautifulSoup

def load_db(path="epl_stats.json"):
    with open(path, "r") as f:
        return json.load(f)

def save_db(db, path="epl_stats.json"):
    with open(path, "w") as f:
        json.dump(db, f, indent=4)

def scrape_premier_league_roster():
    url = "https://fbref.com/en/comps/9/Premier-League-Stats"
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    db = load_db()

    team_table = soup.find("table", id="results2023-2024")
    team_links = team_table.find_all("a")

    for link in team_links:
        href = link.get("href", "")
        if "/squads/" not in href:
            continue

        team_name = link.text.strip()
        team_url = "https://fbref.com" + href

        print(f"Scraping team: {team_name}")

        team_html = requests.get(team_url).text
        team_soup = BeautifulSoup(team_html, "html.parser")

        roster_table = team_soup.find("table", id="stats_standard_9")
        if not roster_table:
            continue

        rows = roster_table.find("tbody").find_all("tr")

        for row in rows:
            player_cell = row.find("th", {"data-stat": "player"})
            if not player_cell:
                continue

            player_link = player_cell.find("a")
            if not player_link:
                continue

            player_name = player_link.text.strip()
            player_href = player_link.get("href")

            parts = player_href.split("/")
            player_id = parts[3]

            db["players"][player_name] = {
                "id": player_id,
                "team": team_name,
                "goals": 0,
                "assists": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "events": []
            }

            print(f"  Added player: {player_name}")

    save_db(db)
    print("Premier League roster scraping complete!")

if __name__ == "__main__":
    scrape_premier_league_roster()
