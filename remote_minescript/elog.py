# pyright: reportUndefinedVariable=false
from minescript import *
import time
import math
import threading
from event_writer import *
# from minescript.system.lib.minescript import chat # no need 
from worldstate import WorldState
import json

world_state = WorldState()

LOG_FILE = "raw_event_log.txt"

def now_format():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    line = f"[{now_format()}] {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    chat(msg)

def distance(now, last):
    dx = now[0] - last[0]
    dy = now[1] - last[1]
    dz = now[2] - last[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)

def direction_vector(from_pos, to_pos):
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    dz = to_pos[2] - from_pos[2]
    direction=""
    if dx > 0:
        direction += "East "
    elif dx < 0:
        direction += "West "
    if dz > 0:
        direction += "South "
    elif dz < 0:
        direction += "North "
    if dy > 0:
        direction += "Up "
    elif dy < 0:
        direction += "Down "
    return (dx, dy, dz, direction)

def format_position(pos):
    return f"({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})"

#----------------on_events-----------------
class CombatAggregate:
    def __init__(self):
        self.sources = {}      # source -> hit count
        self.total_hits = 0
        self.last_health = None
        self.severity = 0.0

    def add(self, event):
        src = event.source or "unknown"
        self.sources[src] = self.sources.get(src, 0) + 1
        self.total_hits += 1
        self.last_health = event.health
        self.severity = max(self.severity, event.severity)

def aggregate_events(events):
    combat = CombatAggregate()

    for e in events:
        if e.type == "under_attack":
            combat.add(e)

    if combat.total_hits == 0:
        return None

    return {
        "type": "under_attack",
        "severity": combat.severity,
        "target": "player",
        "sources": combat.sources,
        "count": combat.total_hits,
        "health": combat.last_health
    }


def on_player_damage(amount, cause, health):
    t = now()
    player_damage_times.append([t,cause])
    player_damage_times[:] = [x for x in player_damage_times if t - x[0] <= UNDER_ATTACK_WINDOW] # keep only recent hits


    # raw event
    if health > 0:
        event_data={
            "type": "player_damage",
            "amount": round(amount, 1),
            "cause": str(cause),
            "health": round(health, 1)
        }
        write_event(event_data)
        world_state.update_event(event_data)
    else:
        event_data={
            "type": "player_death",
            "cause": str(cause)        }
        write_event(event_data)
        world_state.update_event(event_data)

    # aggregate
    if len(player_damage_times) >= UNDER_ATTACK_HITS:
        if not rate_limited("under_attack"):
            event_data = aggregate_events([{
                "type": "under_attack",
                "source": cause,
                "health": health,
                "severity": min(1.0, len(player_damage_times) / UNDER_ATTACK_HITS)
            }])
        if event_data:
            write_event(event_data)
            world_state.update_event(event_data)
        player_damage_times.clear()

def on_victim_damage(victim):
    t = now()
    hits = victim_damage_times.setdefault(victim.id, [])
    hits.append(t)
    hits[:] = [x for x in hits if t - x <= UNDER_ATTACK_WINDOW]

    event_data={
        "type": "victim_damage",
        "mob_id": victim.id,
        "mob": victim.name,
        "health": round(victim.health, 1)
    }
    write_event(event_data)
    world_state.update_event(event_data)

    if len(hits) >= UNDER_ATTACK_HITS:
        event_data={
            "type": "under_attack",
            "target": "mob",
            "mob_id": victim.id,
            "mob": victim.name,
            "cause": "player",
            "intensity": len(hits)
        }
        write_event(event_data)
        world_state.update_event(event_data)
        # print(victim.name, "is under attack by player with", len(hits), "hits!")
        hits.clear()

def check_imminent_threat():
    t = now()
    recent = [m for ts, m in recent_threats if t - ts <= IMMINENT_THREAT_WINDOW]

    if len(recent) >= 2:
        if not rate_limited("imminent_threat"):
            event_data={
                "type": "imminent_threat",
                "mobs": list(set(recent))
            }
            write_event(event_data)
            world_state.update_event(event_data)
        recent_threats.clear()

def on_mob_near(e):
    t = now()
    recent_threats.append((t, e.name))

    event_data={
        "type": "mob_near",
        "mob": e.name,
        "mob_id": e.id
    }
    write_event(event_data)
    world_state.update_event(event_data)

    check_imminent_threat()

def on_mob_incoming(e):
    t = now()
    recent_threats.append((t, e.name))

    event_data={
        "type": "mob_incoming",
        "mob": e.name,
        "mob_id": e.id
    }
    write_event(event_data)
    world_state.update_event(event_data)

    check_imminent_threat()

# ------------------ state ------------------

last_pos = None
last_health = 20.0
global seen_entity_ids
seen_entity_ids = set()

# ------------------ main ------------------
'''SAMPLES
Sample EntityData():
{
    'id': 12345,
    'type': 'entity.minecraft.zombie',
    'name': 'Zombie',
    'position': (x, y, z),
    'health': 20.0,
    'yaw': 0.0,
    'pitch': 0.0
}
Sample DamageEvent(
    type='damage',
    time='',
    entity_uuid='', # damaged target
    cause_uuid='', #(e.g. skeleton shot -> skeleton_uuid, None)
    source='' # (player, skeleton shot -> arrow)
)
Sample player(): uuid, health, name, id
'''
player = get_player()
last_pos = player.position  # tuple (x, y, z)
last_health = player.health # float
last_seen_dangers=[]

log("Event logger started!")
def main():
    global last_pos, last_health, last_seen_dangers, player
    global damage_event
    try:
        player = get_player()  
            # ---- Ceiling blocks ----
        pos = [int (x) for x in player.position]
        ceiling_blocks = get_block_region(pos, [
            pos[0], pos[1]+10, pos[2]
        ]).blocks
        ceiling_blocks = [b[len("minecraft:"):] for b in ceiling_blocks if type(b) is str and b.startswith("minecraft:")]
            # ---- Position ----
        pos_event = {
            "type": "position",
            "x": player.position[0],
            "y": player.position[1],
            "z": player.position[2]
        }
        world_state.update_event(pos_event)

        # ---- Environment ----
        world_state.update_ceiling_blocks(ceiling_blocks)
        block = player_get_targeted_block(20)
        world_state.update_targeted_block(block)

        # ---- Targeted entity ----
        entity = player_get_targeted_entity(20)
        world_state.update_targeted_entity(entity)

        # ---- Hand items ----
        hands = player_hand_items()
        world_state.update_hand_items(hands)

        # ---- Inventory snapshot (optional slower rate) ----
        inv = player_inventory()
        world_state.update_inventory(inv)
    except Exception as e:
        log(f"Warning: Player data not available yet: {e}")

    # ---- damage detection ----

    try: 
        if damage_event.entity_uuid==player.uuid:
            damage = last_health - player.health
            source=damage_event.source
            if source=="mob":
                source_uuid=damage_event.cause_uuid
                for entity in get_entities():
                    if entity.uuid==source_uuid:
                        source=entity.name
                        break
            chat(damage_event)
            log(f"Player took damage ({damage:.1f} HP) by {source} current health {player.health:.1f}")
            on_player_damage(damage,source,player.health)
        elif damage_event.cause_uuid==player.uuid:
            victim=None
            for entity in get_entities():
                if entity.uuid==damage_event.entity_uuid:
                    victim=entity
                    break
            if victim==None:
                log(f"Warning: Victim entity not found for damage event: {damage_event}")
            else:
                log(f"#{victim.id} {victim.name} took damage by player current health {victim.health}")
            on_victim_damage(victim)
    except:
        log("Warning: No damage listener yet")
        

    # ---- low health warning ----
    if player.health <= 5.0 and last_health > 5.0:
        log(f"Warning: Player health is {player.health:.1f} HP!")
        write_event({
            "type": "player_low_health",
            "health": round(player.health, 1)
        })
        world_state.update_event({
            "type": "player_low_health",
            "health": round(player.health, 1)
        })


    last_pos = player.position
    last_health = player.health
last_danger_distances = {}
def periodic_danger_check():
    # ---- nearby hostile mobs ----
    # for e in entities(): echo(e['name'])
    player=get_player()
    HOSTILES = ["creeper","zombie","skeleton","spider","enderman","witch","drowned","husk","stray","phantom","pillager","ravager","evoker","vindicator"]
    for e in get_entities():
        if not any(monster in e.type for monster in HOSTILES):
            continue

        dist_now = distance(player.position, e.position)

        if dist_now > 8:
            if e.id in last_danger_distances:
                del last_danger_distances[e.id]
            continue

        if e.id not in last_danger_distances:
            last_danger_distances[e.id] = dist_now
            continue

        dist_before = last_danger_distances[e.id]

        if abs(dist_now - dist_before) < 2:
            continue  # ignore micro jitter

        if dist_now < dist_before:
            log(f"Incoming #{e.id} {e.name}!")
            on_mob_incoming(e)

        elif dist_now > dist_before:
            log(f"Distancing from #{e.id} {e.name}...")
            write_event({
                "type": "mob_retreat",
                "mob_id": e.id,
                "mob": e.name
            })

        last_danger_distances[e.id] = dist_now  
    threading.Timer(1, periodic_danger_check).start()


def damage_check():
    main()

RESPONSE_FILE = "response_log.txt"
last_response=""
with EventQueue() as eq:
    eq.register_damage_listener()
    eq.register_chat_listener()
    # event = eq.get()
    echo("Event listeners registered...")
    echo("Please wait... Running checks...")

    damage_check()
    periodic_danger_check()
    echo("Checks ran successfully")
    while True:
        event = eq.get()
        if event.type == EventType.DAMAGE:
            damage_event=event
            damage_check()
            state=world_state.export()
            # write_world_state(state)
            # delay to ensure state is updated before AI reads it
            time.sleep(0.1)
            write_world_state(state)
        # if event.type == EventType.CHAT:
        #     print(msg := event.message)
        
        # with open(RESPONSE_FILE, "r", encoding="utf-8") as rf:
        #     response_data = rf.read()
        #     if response_data != last_response:
        #         last_response = response_data
        #         echo("New response generated:")
        #         echo(last_response)
        
        #     if msg =="Damage event detected":
        #         echo(msg+" from chat")




