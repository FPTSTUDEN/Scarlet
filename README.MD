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

### Example

> - Relax, you've got this! Just a little more precision and those mobs will be history. (imminent_threat)
> - Nice going there, Caspar the friendly zombie's new best friend! (under_attack)
> - Well, that's one way to become a zombie's favorite snack. Better luck next time! (player_death)

## Stable files

- **remote_minescript/elog.py** - event logger to /.minecraft/minescript/single_event.log
- **main.py** - Main AI engine

## Tech stack

- **Minecraft** with **Minescript** mod
- **Python** for prompting-related functions
- **Ollama**: dolphin3:latest

## TODO

### Logging

(...: in progress, V: Done, X: Failed attempt)

- [x] **under_attack aggregator**
- [x] Refactored `biotrack` into class & usage in `elog`
- [ ] Type definitions
- [ ] Ignoring blocked hostile (get_block_region has block)
- [ ] Detailed underground checks
- [ ] Ingame chat
- [ ] Style chat overlay & reactions
- [ ] achievement
- ~~lava_near~~ (no need)

- [ ] Player action (long duration): mining, farming,...
- [ ] Inventory: collective, should be new items only

### Memory

- [x] death count (+ reason for death)

## Credits

See [credits.md](./credits.md)
