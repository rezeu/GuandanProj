# Guandan Card Type Definition Files

## Overview
Created Guandan-specific card type definition files to replace the DouDizhu files that were being used in the Guandan game implementation.

## Files Created

### `/mnt/c/Files/Course/RL/rlcard/rlcard/games/guandan/jsondata/action_space.txt`
- **Size**: 2,478 bytes
- **Content**: Space-separated list of 400 valid card combinations in Guandan
- **Includes**: All valid single cards, pairs, triples, full houses, straights, tubes, plates, bombs, and the pass action

### `/mnt/c/Files/Course/RL/rlcard/rlcard/games/guandan/jsondata/card_type.json`
- **Size**: 11,018 bytes
- **Content**: JSON mapping from card combination string to card type and weight
- **Format**: `{"combination": [["type", "weight"]]}`
- **Example**: `"33344": [["full_house", "0"]]`

### `/mnt/c/Files/Course/RL/rlcard/rlcard/games/guandan/jsondata/type_card.json`
- **Size**: 4,476 bytes
- **Content**: JSON mapping from card type to possible combinations
- **Format**: `{"type": {"weight": ["combination1", "combination2", ...]}}`

## Card Types Supported

### Regular Card Types (7 types as per Guandan rules)
1. **solo** - Single cards (3, 4, 5, ..., K, A, 2, B, R)
2. **pair** - Pairs of same rank (33, 44, ..., RR)
3. **triple** - Three of same rank (333, 444, ..., RRR)
4. **full_house** - Triple + pair (33344, 33355, etc.)
5. **straight** - 5+ consecutive cards in natural order (34567, 45678, etc.)
6. **tube** - 3 consecutive pairs (334455, 445566, etc.)
7. **plate** - 2 consecutive triples (333444, 444555, etc.)

### Bomb Types (Special combinations that beat regular cards)
8. **bomb_4** - Four of same rank (4444, 5555, etc.)
9. **bomb_5** - Five of same rank (55555, 66666, etc.)
10. **bomb_6** - Six of same rank (666666, 777777, etc.)
11. **bomb_7** - Seven of same rank (7777777, 8888888, etc.)
12. **bomb_8** - Eight of same rank (88888888, 99999999, etc.)
13. **joker_bomb** - Both jokers (BR) - highest bomb

## Key Differences from DouDizhu

### 4-Player Support
- Designed for 4 players (0&2 vs 1&3 teams)
- Team-based gameplay considerations

### Guandan-Specific Combinations
- **Tubes** (3 consecutive pairs) - unique to Guandan
- **Plates** (2 consecutive triples) - unique to Guandan
- **Extended bombs** (up to 8 of same rank) - supports multiple decks

### Level Card System Ready
- Card ranking supports level card system
- Wild card functionality can be implemented on top

### Updated Utils Functions
- Modified `utils.py` to load Guandan-specific files
- Updated `get_gt_cards()` for Guandan card hierarchy
- Renamed `get_landlord_score()` to `get_guandan_score()` with bomb scoring

## Usage
The Guandan game implementation now uses these files instead of the DouDizhu ones:
- `CARD_TYPE` - Maps card combinations to their types
- `TYPE_CARD` - Maps card types to possible combinations  
- `ID_2_ACTION` / `ACTION_2_ID` - Action space mappings

## Testing
All files have been tested and verified to load correctly with the proper Guandan card combinations and types.