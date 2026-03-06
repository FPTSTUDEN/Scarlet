# worldstate.py

from collections import Counter, deque
import time


class WorldState:
    def __init__(self):
        # -------- Position --------
        self.depth_history = deque(maxlen=20)
        self.vertical_trend = 0.0

        # -------- Combat --------
        self.recent_hits = deque(maxlen=10)
        self.mob_encounters = Counter()
        self.combat_intensity = 0.0

        # -------- Targeting --------
        self.targeted_block = None
        self.targeted_entity = None

        # -------- Inventory --------
        self.main_hand = None
        self.off_hand = None
        self.inventory_summary = Counter()

        # -------- Environment --------
        self.current_biome = None
        self.biome_enter_time = None
        self.underground = False
        self.darkness = False

        # -------- Health --------
        self.health = 20.0

    # ====================================
    # Public Update Entry
    # ====================================

    def update_event(self, event: dict):
        etype = event.get("type")

        if etype == "player_damage":
            self._update_damage(event)

        elif etype == "under_attack":
            self._update_attack(event)

        elif etype == "mob_near":
            self.mob_encounters[event.get("mob")] += 1

        elif etype == "biome_enter":
            self.current_biome = event.get("biome")
            self.biome_enter_time = event.get("enter_time")

        elif etype == "position":
            self._update_position(event)

        self._infer()

    # ====================================
    # Direct Sensor Updates
    # ====================================
    def update_ceiling_blocks(self, blocks):
        # print(blocks)
        # This can be called directly from the elog loop when we fetch ceiling blocks
        current_y = self.depth_history[-1] if self.depth_history else 61
        # print(f"Current Y: {current_y}")
        under_roof = False
        under_cave=False
        for block in blocks:
            if block not in ["air", "cave_air"]:
                under_roof = True
                if block in ["stone", "deepslate", "granite", "diorite", "andesite"]:
                    under_cave = True
        # print(f"Under roof: {under_roof}, Under cave: {under_cave}")
        self.underground = current_y < 20 or (under_roof and under_cave and (current_y < 62))
        # print(f"Updated underground status: {self.underground}")
    def update_targeted_block(self, block):
        if block:
            self.targeted_block = block.type
        else:
            self.targeted_block = None

    def update_targeted_entity(self, entity):
        if entity:
            self.targeted_entity = entity.name
        else:
            self.targeted_entity = None

    def update_hand_items(self, hand_items):
        if hand_items:
            self.main_hand = hand_items.main_hand["item"] if hand_items.main_hand else None
            self.off_hand = hand_items.off_hand["item"] if hand_items.off_hand else None

    def update_inventory(self, items):
        self.inventory_summary.clear()
        for item in items:
            if item and item.item:
                self.inventory_summary[item.item] += item.count

    # ====================================
    # Internal State Updates
    # ====================================

    def _update_damage(self, event):
        self.health = event.get("health", self.health)
        self.recent_hits.append(time.time())

    def _update_attack(self, event):
        self.recent_hits.append(time.time())
        sources = event.get("sources", {})
        for s, count in sources.items():
            self.mob_encounters[s] += count

    def _update_position(self, event):
        y = event.get("y")
        if y is not None:
            self.depth_history.append(y)

    # ====================================
    # Inference Layer
    # ====================================

    def _infer(self):
        self._infer_vertical()
        self._infer_combat()
        # self._infer_environment()  # Environment inference now relies on direct ceiling block updates

    def _infer_vertical(self):
        if len(self.depth_history) < 6:
            return
        first = list(self.depth_history)[:3]
        last = list(self.depth_history)[-3:]
        self.vertical_trend = sum(last)/3 - sum(first)/3

    def _infer_combat(self):
        now = time.time()
        window = 5
        recent = [t for t in self.recent_hits if now - t <= window]
        self.combat_intensity = len(recent) / window

    def _infer_environment(self, ceiling_blocks=None):
        # 1. Depth Check (Standard sea level is ~63)
        current_y = self.depth_history[-1] if self.depth_history else 64
        
        # 2. Ceiling Check
        # Pass the block type above the player into this method
        under_roof = False
        if ceiling_blocks:
            for block in ceiling_blocks:
                if block not in ["air", "cave_air"]:
                    under_roof = True
                    break

        # If deep enough or under heavy cover, we are "underground"
        self.underground = current_y < 50 or (under_roof and current_y < 62)

        # Darkness logic (Combat + Underground is a good proxy for 'danger/dark')
        self.darkness = self.underground and self.combat_intensity > 0.2

    # ====================================
    # Export for AI
    # ====================================

    def export(self):
        return {
            "health": self.health,
            "combat_intensity": round(self.combat_intensity, 2),
            "vertical_trend": round(self.vertical_trend, 2),
            "mob_encounters": dict(self.mob_encounters),
            "targeted_block": self.targeted_block,
            "targeted_entity": self.targeted_entity,
            "main_hand": self.main_hand,
            "inventory_summary": dict(self.inventory_summary),
            "underground": self.underground,
            "darkness": self.darkness,
            "biome": self.current_biome
        }