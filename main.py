import os
import itertools

# List of bot names
bots = ["RBC1.py", "rand.py", "trout.py", "reconchess.bots.random_bot"]

# Generate all unique pairings of bots
pairings = list(itertools.combinations(bots, 2))

# Run the matches
for bot1, bot2 in pairings:
    # Bot 1 plays as white, Bot 2 plays as black
    print(f"python -m reconchess.scripts.rc_bot_match \"{bot1}\" \"{bot2}\"")
    os.system(f"python -m reconchess.scripts.rc_bot_match \"{bot1}\" \"{bot2}\"")

    # Bot 2 plays as white, Bot 1 plays as black
    print(f"python -m reconchess.scripts.rc_bot_match \"{bot2}\" \"{bot1}\"")
    os.system(f"python -m reconchess.scripts.rc_bot_match \"{bot2}\" \"{bot1}\"")
