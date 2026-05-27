import json

def load_db(path="epl_stats.json"):
    with open(path, "r") as f:
        return json.load(f)

def find_player(db, name):
    name = name.lower()
    for player in db["players"]:
        if player.lower() == name:
            return player
    return None

def get_nth_event(player_data, event_type, number):
    for event in player_data["events"]:
        if event["type"] == event_type and event["index"] == number:
            return event["match"]
    return None

def chatbot():
    db = load_db()

    print("Hello! What player would you like to learn about.")

    while True:
        user = input("> ").strip()

        if user.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break

        # Find player
        player_name = find_player(db, user)
        if not player_name:
            print("I couldn't find that player. Try another name.")
            continue

        pdata = db["players"][player_name]

        print(f"\nStats for {player_name}:")
        print(f"Goals: {pdata['goals']}")
        print(f"Assists: {pdata['assists']}")
        print(f"Yellow cards: {pdata['yellow_cards']}")
        print(f"Red cards: {pdata['red_cards']}\n")

        print("You can ask:")
        print("- what game did he score 3")
        print("- what game did he assist 2")
        print("- what game did he get yellow 1")
        print("- or type another player name\n")

        while True:
            q = input("> ").strip().lower()

            if q in ["back", "player", "new player"]:
                print("\nOkay, who next?")
                break

            parts = q.split()
            if len(parts) < 5:
                print("Try asking: what game did he score 2")
                continue

            # Parse question
            number = int(parts[-1])
            event_word = parts[-2]

            if event_word == "score" or event_word == "scored":
                event_type = "goal"
            elif event_word == "assist" or event_word == "assisted":
                event_type = "assist"
            elif event_word == "yellow":
                event_type = "yellow"
            elif event_word == "red":
                event_type = "red"
            else:
                print("I didn't understand that event.")
                continue

            match = get_nth_event(pdata, event_type, number)
            if match:
                print(f"{player_name}'s {number}th {event_type} was in: {match}")
            else:
                print(f"I couldn't find that event.")

if __name__ == "__main__":
    chatbot()
