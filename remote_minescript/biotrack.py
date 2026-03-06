# pyright: reportUndefinedVariable=false
from minescript import *
import time
global BIOMES
global b_count
global b_current
from event_writer import write_event
# from worldstate import WorldState
# world_state = WorldState()
t_begin=time.time()


class BiomeTracker:
    def __init__(self):
        echo("Initializing BiomeTracker...")
        self.current_biome = None
        self.biome_enter_time = None
        self.underground = False
        self.darkness = False
        self.BIOMES = [
    "the_void", "plains", "sunflower_plains", "snowy_plains", "ice_spikes",
    "desert", "swamp", "mangrove_swamp", "forest", "flower_forest",
    "birch_forest", "dark_forest", "old_growth_birch_forest", "old_growth_pine_taiga",
    "old_growth_spruce_taiga", "taiga", "snowy_taiga", "savanna", "savanna_plateau",
    "windswept_hills", "windswept_gravelly_hills", "windswept_forest",
    "windswept_savanna", "jungle", "sparse_jungle", "bamboo_jungle",
    "badlands", "eroded_badlands", "wooded_badlands", "meadow", "cherry_grove",
    "grove", "snowy_slopes", "frozen_peaks", "jagged_peaks", "stony_peaks",
    "river", "frozen_river", "beach", "snowy_beach", "stony_shore",
    "warm_ocean", "lukewarm_ocean", "deep_lukewarm_ocean", "ocean", "deep_ocean",
    "cold_ocean", "deep_cold_ocean", "frozen_ocean", "deep_frozen_ocean",
    "mushroom_fields", "dripstone_caves", "lush_caves", "deep_dark"
]
        BIOMES_NETHER = [
            "nether_wastes", "soul_sand_valley", "crimson_forest", "warped_forest",
            "basalt_deltas"
        ]
        BIOMES_END = ["the_end", "end_highlands", "end_midlands", "small_end_islands", "end_barrens" ]
        self.BIOMES.extend(BIOMES_NETHER)
        self.BIOMES.extend(BIOMES_END)
        self.b_count={}
        for b in self.BIOMES: self.b_count[b]={"duration":0,"count":0}
        execute('gamerule commandBlockOutput false')
        execute('execute unless entity @e[tag=biome,limit=1] run summon minecraft:armor_stand ~ ~ ~ {Invisible:true,Invulnerable:true,NoBasePlate:true,NoGravity:true,Small:true,Marker:true,Tags:["biome"]}')
    def check_biomes(self):
        execute('execute at @p run tp @e[tag=biome] ~ ~ ~')
        # echo("Checking biomes...")
        x, y, z = map(int, player_position())
        for b in self.BIOMES:
            full_biome = f"minecraft:{b}"
            execute(
                f"/execute "
                f"if biome {x} {y} {z} {full_biome} "
                f"run data merge entity @e[type=armor_stand,limit=1,tag=biome] "+"{Invisible:0b,Tags:[\"biome\",\"1\"],"
                f"CustomName:'\"{b}\"'"+"}"
            )
        # for e in get_entities():
        #      if "armor_stand" in e.type: print(e)
        for b in self.BIOMES:
            name='\"'+b+'\"'
            if get_entities(name=name)!=[]:
                e=get_entities(name=name)[0]
                # b=e.name
                # echo(f"now {b} prev {self.current_biome}")
                if (b!=self.current_biome):
                    if (self.current_biome==None):
                        echo(f"entered {b}")
                        write_event({"type":"biome_enter", "biome":b})
                        self.b_count[b]['count']+=1
                    else:
                        echo(f"leaving {self.current_biome}, stayed for {self.b_count[self.current_biome]['duration']}")
                        echo(f"entering {b} for the {self.b_count[b]['count']+1} time")
                        write_event({"type":"biome_exit", "biome":self.current_biome, "stay_time":self.b_count[self.current_biome]['duration'], "entered_biome":b, "entered_biome_count":self.b_count[b]['count']+1})
                        # write_event({"type":"biome_enter", "biome":b})
                        self.b_count[self.current_biome]['duration']=0
                        self.b_count[b]['count']+=1
                # echo(f"staying for {self.b_count[b]['duration']} total {self.b_count[b]['count']}")
                self.current_biome=b
                self.b_count[b]['duration']+=1
                # echo(b)
                # time.sleep(1)
                return {
                    "biome": b,
                    "biome_enter_time": self.biome_enter_time

                }
# biometracker=BiomeTracker()
# while True:
#     biometracker.check_biomes()
#     time.sleep(1)