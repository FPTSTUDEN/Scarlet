
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
from dataclasses import dataclass
from enum import Enum


WORLD_STATE_FILE = "new_minescript/world_state.json"

def load_world_state():
    try:
        with open(WORLD_STATE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
class Atmosphere(Enum):
    CALM = "calm"
    TENSE = "tense"
    CLAUSTROPHOBIC = "claustrophobic"
    TRIUMPHANT = "triumphant"
    SOMBER = "somber"


@dataclass
class DerivedState:
    threat: float
    loss: bool
    exploration_shift: bool


@dataclass
class ImmersionContext:
    atmosphere: str
    tone: str
    initiative_bias: float


def build_derived_state(event: GameEvent, state: dict, world: dict) -> DerivedState:

    threat = event.severity

    # Add ambient pressure
    darkness = world.get("darkness", 0)
    underground = world.get("underground", False)

    ambient_pressure = darkness * 0.4 + (0.3 if underground else 0)

    threat = min(1.0, threat + ambient_pressure)

    loss = event.type == "player_death"
    exploration_shift = event.type in ["biome_enter", "biome_exit"]

    return DerivedState(
        threat=threat,
        loss=loss,
        exploration_shift=exploration_shift
    )

def build_immersion_context(derived: DerivedState, mood: dict, world: dict) -> ImmersionContext:

    stress = mood["stress"]
    confidence = mood["confidence"]

    if derived.loss:
        atmosphere = Atmosphere.SOMBER.value
        tone = "quiet"
    elif derived.threat > 0.7:
        atmosphere = Atmosphere.TENSE.value
        tone = "urgent"
    elif derived.exploration_shift and confidence > 0.6:
        atmosphere = Atmosphere.TRIUMPHANT.value
        tone = "uplifted"
    elif stress > 0.6:
        atmosphere = Atmosphere.CLAUSTROPHOBIC.value
        tone = "whispered"
    else:
        atmosphere = Atmosphere.CALM.value
        tone = "soft"

    initiative_bias = max(0.1, min(1.0, 0.4 + stress * 0.3 + confidence * 0.2))

    return ImmersionContext(
        atmosphere=atmosphere,
        tone=tone,
        initiative_bias=round(initiative_bias, 2)
    )
def get_severity(event_type: str) -> float:
    severity = EVENT_SEVERITY.get(event_type, DEFAULT_SEVERITY)
    return severity if severity is not None else DEFAULT_SEVERITY

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

def build_prompt(event: GameEvent, mood: dict, immersion: dict, world: dict):
    urgency = (
        "critical" if event.severity >= 0.85 else
        "high" if event.severity >= 0.5 else
        "low"
    )

    situation = []

    if event.type == "under_attack":
        situation.append(
            f"Under sustained attack ({event.intensity} hits)"
        )

    elif event.type == "imminent_threat":
        situation.append(
            f"{len(event.mobs)} hostile mobs closing in"
        )

    elif event.type == "player_low_health":
        situation.append(
            f"Health critically low ({event.health:.1f} HP)"
        )

    elif event.type == "player_death":
        situation.append(
            f"Player died due to {event.cause}"
        )

    elif event.type == "biome_enter":
        situation.append(
            f"Entered {event.biome} biome"
        )

    elif event.type == "biome_exit":
        situation.append(
            f"Left {event.biome} biome"
        )

    else:
        situation.append(str(event.type))

    return f"""
Atmosphere: {immersion['atmosphere']}
Tone: {immersion['tone']}
Initiative bias: {immersion['initiative_bias']}

Environment:
- Biome: {world.get('biome', 'unknown')}
- Underground: {world.get('underground', False)}
- Darkness: {world.get('darkness', 0)}

Situation:
- {'; '.join(situation)}
- Urgency: {urgency}

Player mood:
- Stress: {mood['stress']:.2f}
- Confidence: {mood['confidence']:.2f}
""".strip()
SEVERITY_THRESHOLD = 0.3  # tune this

def handle_event(event: GameEvent):
    state = load_state()
    world_state = load_world_state()

    severity = get_severity(event.type)
    if severity is None:
        severity = DEFAULT_SEVERITY
    event.severity = severity

    update_state(state, event)

    # --- Immersion Layer ---
    derived = build_derived_state(event, state, world_state)
    immersion = build_immersion_context(derived, state["mood"], world_state)

    state["immersion"] = {
        "atmosphere": immersion.atmosphere,
        "tone": immersion.tone,
        "initiative_bias": immersion.initiative_bias
    }

    # --- Severity Gate ---
    if severity < SEVERITY_THRESHOLD:
        save_state(state)
        return

    if not should_comment(state, event):
        save_state(state)
        return

    intent = decide_intent(state, event)

    prompt = build_prompt(
    event,
    state["mood"],
    state["immersion"],
    world_state
)
    print("Generated prompt:", prompt)
    response = generate_response(prompt)
    responses.append(response)

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