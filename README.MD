<!-- ![banner](./.misc/crimson%20banner%20-%20ChatGPT.png) -->
<h1 align="center">
    <img src="./.misc/crimson banner - ChatGPT2.png" width="100%"/>
    <br>
    <!-- Scarlet King -->
    <!-- <br> -->
</h1>

<!-- # Scarlet -->
> **[InLava]** Well, that was hot. Not literally, I hope?

An AI companion that watches a Minecraft session in real time, understands what's happening (combat, danger, death, biomes), *and reacts live inside the game using in-game chat* (in progress).

## Features

- Observes live gameplay events via MineScript
- Aggregates raw events into situations (since I dont have a data center to process every event lol)
- Uses a local LLM to generate short, emotional reactions
- *Speaks directly in Minecraft chat* (in progress)
- Adapts tone based on danger, stress, and context (pending improvements)

## Examples

```
- Relax, you've got this! Just a little more precision and those mobs will be history. (imminent_threat)
- Nice going there, Caspar the friendly zombie's new best friend! (under_attack)
- Well, that's one way to become a zombie's favorite snack. Better luck next time! (player_death)
```


## Stable files

- **remote_minescript/elog.py** - event logger to /.minecraft/events.txt
- **remote_minescript/biotrack.py** - biome & time on biome logger
- **main.py** - THE AI: one-time parses events.log for now

## Tech stack

- **Minecraft** with **Minescript** mod
- **Python** for prompting-related functions
- **Ollama**: dolphin3:latest

## TODO

### Logging

(...: in progress, V: Done, X: Failed attempt)

- [x] **under_attack aggregator**
- [x] **damaged** (cause: lava,monster...)
- [x] **attacked entity**
- death ... (0 HP detection possible)
- [x] **low_health** 
- [x] **monster_near**
- [ ] achievement
- [x] enter_dimension/ **biome**
- ~~lava_near~~ (no need)

- [] Player action (long duration): mining, farming,...
- [] Inventory: collective, should be new items only

### Log parser -> comment

- Danger situation (cheer up/feel pity...)
- above logs...

### Memory

- death count (+ reason for death)

## Credits

See [credits.md](./credits.md)
