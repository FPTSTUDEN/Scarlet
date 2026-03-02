import json
from llm.client import generate_response
from emotion.engine import update_state, decide_intent, should_comment
from events.event_schema import GameEvent
from events.severity import EVENT_SEVERITY, DEFAULT_SEVERITY
from events.event_reader import replay_events, replay_single_event
import time
from dotenv import load_dotenv
import os
load_dotenv()
def get_severity(event_type: str) -> float:
    return EVENT_SEVERITY.get(event_type, DEFAULT_SEVERITY)

# PERSONALITY = {
#     "talkativeness": 0.35,   # lower = more silence
#     "sarcasm": 0.4,
#     "empathy": 0.6,
#     "urgency_bias": 0.5
# }

STATE_FILE = "state/companion_state.json"
def reset_state():
    initial_state = {
        "mood": {
            "stress": 0.2,
            "confidence": 0.8,
        },
        "stats": {
            "recent_deaths": 0,
            "last_comment_time": 0.0,
            "last_comment_topic": "",
        }
    }
    with open(STATE_FILE, "w") as f:
        json.dump(initial_state, f, indent=2)

def describe_event(event):
    t = event.type

    if t == "under_attack":
        if getattr(event, "target", "") == "player":
            return f"The player is under sustained attack ({event.intensity} hits)."
        return f"A {event.mob} is under heavy attack."

    if t == "imminent_threat":
        return f"Multiple hostile mobs are closing in: {', '.join(event.mobs)}."

    if t == "death":
        return f"The player just died due to {event.cause}."

    if t == "biome_enter":
        return f"The player entered the {event.biome} biome."

    if t == "biome_exit":
        return f"The player left the {event.biome} biome after a long stay."

    if t == "low_health":
        return "The player's health is critically low."

    return f"Event occurred: {t}."


def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def build_prompt(event: GameEvent, mood: dict):
    print(event.type,event.severity)
    urgency = (
        "critical" if event.severity >= 0.85 else
        "high" if event.severity >= 0.5 else #0.6 -> 0.5
        "low"
    )

    situation = []

    if event.type == "under_attack":
        if event.target == "player":
            situation.append(
                f"You are under sustained attack ({event.intensity} hits)"
            )
        else:
            situation.append(
                f"A {event.mob} is under heavy attack ({event.intensity} hits)"
            )

    elif event.type == "imminent_threat":
        situation.append(
            f"Hostile mobs are closing in ({len(event.mobs)} nearby)"
        )

    elif event.type == "player_low_health":
        situation.append(
            f"Health is critically low ({event.health:.1f} HP)"
        )

    elif event.type == "player_death":
        situation.append(
            f"You just died due to {event.cause}"
        )

    elif event.type == "biome_enter":
        situation.append(
            f"You entered the {event.biome} biome"
        )

    elif event.type == "biome_exit":
        situation.append(
            f"You spent {event.stay_time} seconds in the {event.biome} biome. Now entering {event.entered_biome} biome (for the {event.entered_biome_count} time)."
        )
    else: 
        print(f"-----{event.type}-----")
        situation.append(str(event.type))
    print(situation)

    return f"""

Situation:
- {'; '.join(situation)}
- Urgency: {urgency}

Player state:
- Stress: {mood['stress']:.2f}
- Confidence: {mood['confidence']:.2f}


""".strip()
# short sentences modification
# Removed: Stay in character. 

SEVERITY_THRESHOLD = 0.3  # tune this

def handle_event(event: GameEvent):
    state = load_state()

    severity = get_severity(event.type)
    event.severity = severity  # attach for prompt use

    update_state(state, event)

    # --- new gate ---
    if severity < SEVERITY_THRESHOLD:
        save_state(state)
        return
    # ----------------

    if not should_comment(state, event):
        save_state(state)
        return

    intent = decide_intent(state, event)
    prompt = build_prompt(event, state["mood"])  # pass mood dict, not intent

    response = generate_response(prompt)
    responses.append(response)

    # print("AI:", response)
    # print(event.type, "| Severity:", severity, "| Timestamp:", event.timestamp)

    save_state(state)


# ---- TEST ----
MINESCRIPT__PATH=os.getenv("MINESCRIPT_PATH")
SINGLE_EVENT_LOG_FILE=MINESCRIPT__PATH+"single_event.log"
RESPONSE_LOG_FILE=MINESCRIPT__PATH+"response_log.txt"
if __name__ == "__main__":
    with open(SINGLE_EVENT_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
    reset_state()
    global responses
    responses=[]
    last_event_data = GameEvent(type="none", timestamp=0)
    last_response_time = 0
    print("Starting event monitoring loop...")
    while True:
        with open(SINGLE_EVENT_LOG_FILE, "r", encoding="utf-8") as f:
            for event in replay_single_event(SINGLE_EVENT_LOG_FILE):
                if event.timestamp>last_event_data.timestamp:
                    # print(event.timestamp,last_event_data.timestamp)
                    handle_event(event)
                    last_event_data = event
                    for res in responses:
                        print("New response:", res)
                        with open(RESPONSE_LOG_FILE, "w", encoding="utf-8") as rf:
                            rf.write(res + "\n")
                        time.sleep(0.1)  # slight delay to ensure file write
                    responses = []

            


'''
1. add debug printing for relevant parameters: should-comment, saved state... after each iteration
2. add minor logic fixes so overall structure is more refined
'''