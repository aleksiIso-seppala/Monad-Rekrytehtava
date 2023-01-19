from dotenv import dotenv_values
import requests
import webbrowser
import websocket
import json
from lib.math import normalize_heading
import time

FRONTEND_BASE = "noflight.monad.fi"
BACKEND_BASE = "noflight.monad.fi/backend"

game_id = None

def on_message(ws: websocket.WebSocketApp, message):
    [action, payload] = json.loads(message)

    if action != "game-instance":
        print([action, payload])
        return

     # New game tick arrived!
    game_state = json.loads(payload["gameState"])
    commands = generate_commands(game_state)

    time.sleep(0.1)
    ws.send(json.dumps(["run-command", {"gameId": game_id, "payload": commands}]))


def on_error(ws: websocket.WebSocketApp, error):
    print(error)


def on_open(ws: websocket.WebSocketApp):
    print("OPENED")
    ws.send(json.dumps(["sub-game", {"id": game_id}]))


def on_close(ws, close_status_code, close_msg):
    print("CLOSED")


# Change this to your own implementation
def generate_commands(game_state):
    commands = []

    for aircraft in game_state["aircrafts"]:

        id = aircraft['id'];

        aircraft_x = aircraft['position']['x']
        aircraft_x = float(aircraft_x)
        aircraft_y = aircraft['position']['y']
        aircraft_y = float(aircraft_y)

        dir = normalize_heading(aircraft['direction'])

        # all turns made by craft 3
        if id == '3':
            if aircraft_x > -10:

                # first turn
                if dir != 190:
                    new_dir = normalize_heading(aircraft['direction'] - 20)
                    commands.append(f"HEAD {aircraft['id']} {new_dir}")

            # correcting turn
            elif dir != 270:
                new_dir = normalize_heading(aircraft['direction'] + 20)
                commands.append(f"HEAD {aircraft['id']} {new_dir}")

        # crafts 1 and 2 use the same trajectory and they are handled here
        else:
            if aircraft_y > 50:

                # first turn to avoid craft 3
                if dir != 250:
                    new_dir = normalize_heading(aircraft['direction'] - 10)
                    commands.append(f"HEAD {aircraft['id']} {new_dir}")

            # correcting angle, this is done last
            elif aircraft_y < -50:
                if dir != 270:
                    new_dir = normalize_heading(aircraft['direction'] - 10)
                    commands.append(f"HEAD {aircraft['id']} {new_dir}")

            # correcting course toward airports
            elif dir != 290:
                new_dir = normalize_heading(aircraft['direction'] + 20)
                commands.append(f"HEAD {aircraft['id']} {new_dir}")

    return commands

def main():
    config = dotenv_values()
    res = requests.post(
        f"https://{BACKEND_BASE}/api/levels/{config['LEVEL_ID']}",
        headers={
            "Authorization": config["TOKEN"]
        })

    if not res.ok:
        print(f"Couldn't create game: {res.status_code} - {res.text}")
        return

    game_instance = res.json()

    global game_id
    game_id = game_instance["entityId"]

    url = f"https://{FRONTEND_BASE}/?id={game_id}"
    print(f"Game at {url}")
    webbrowser.open(url, new=2)
    time.sleep(2)

    ws = websocket.WebSocketApp(
        f"wss://{BACKEND_BASE}/{config['TOKEN']}/", on_message=on_message, on_open=on_open, on_close=on_close, on_error=on_error)
    ws.run_forever()


if __name__ == "__main__":
    main()