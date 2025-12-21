"""
Core card utilities for Guandan v2
Lightweight implementation using pure IDs and batch conversion functions
"""

# ============================================================================
# Card ID Mapping (0-107)
# Deck: Double deck (108 cards)
# Suit order: Hearts(♥), Diamonds(♦), Clubs(♣), Spades(♠)
# Cards: 3, 4, 5, 6, 7, 8, 9, T, J, Q, K, A, 2, BJ, RJ
# ============================================================================

# Pre-computed mappings for O(1) lookup
CARD_ID_TO_RANK = []
CARD_ID_TO_SUIT = []
CARD_ID_TO_VALUE = []  # 0-14 for comparison

# Rank ordering (low to high)
RANK_ORDER = ['3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A', '2', 'BJ', 'RJ']
RANK_TO_VALUE = {rank: i for i, rank in enumerate(RANK_ORDER)}

# Suit symbols
SUITS = ['♥', '♦', '♣', '♠', 'BJ', 'RJ']
SUIT_ORDER = {'♥': 0, '♦': 1, '♣': 2, '♠': 3, 'BJ': 4, 'RJ': 5}

def _init_card_mappings():
    """Initialize card ID mappings (called once at import)"""
    global CARD_ID_TO_RANK, CARD_ID_TO_SUIT, CARD_ID_TO_VALUE
    
    CARD_ID_TO_RANK = []
    CARD_ID_TO_SUIT = []
    CARD_ID_TO_VALUE = []
    
    # Generate mappings for 108 cards (double deck)
    for deck in range(2):  # Two decks
        deck_offset = deck * 54  # 54 cards per deck
        
        # Add regular cards for each suit
        for suit_idx in range(4):  # 4 suits: ♥, ♦, ♣, ♠
            suit = SUITS[suit_idx]
            for rank_idx in range(13):  # 13 ranks: 3-2
                rank = RANK_ORDER[rank_idx]
                value = rank_idx
                
                CARD_ID_TO_RANK.append(rank)
                CARD_ID_TO_SUIT.append(suit)
                CARD_ID_TO_VALUE.append(value)
        
        # Add jokers
        for joker_rank in ['BJ', 'RJ']:
            rank_idx = RANK_ORDER.index(joker_rank)
            rank = RANK_ORDER[rank_idx]
            value = rank_idx
            
            CARD_ID_TO_RANK.append(rank)
            CARD_ID_TO_SUIT.append(joker_rank)  # BJ or RJ
            CARD_ID_TO_VALUE.append(value)

# Initialize mappings on import
_init_card_mappings()

# ============================================================================
# Batch Conversion Functions
# ============================================================================

def ids_to_ranks(card_ids):
    """
    Convert card IDs to ranks (batch operation)
    
    Args:
        card_ids: List of card IDs (0-107)
        
    Returns:
        List of rank strings
    """
    return [CARD_ID_TO_RANK[i] for i in card_ids]

def ids_to_suits(card_ids):
    """
    Convert card IDs to suits (batch operation)
    
    Args:
        card_ids: List of card IDs (0-107)
        
    Returns:
        List of suit strings
    """
    return [CARD_ID_TO_SUIT[i] for i in card_ids]

def ids_to_values(card_ids):
    """
    Convert card IDs to comparison values (batch operation)
    
    Args:
        card_ids: List of card IDs (0-107)
        
    Returns:
        List of integer values (0-14)
    """
    return [CARD_ID_TO_VALUE[i] for i in card_ids]

def ids_to_pairs(card_ids):
    """
    Convert card IDs to (rank, suit) pairs (batch operation)
    
    Args:
        card_ids: List of card IDs (0-107)
        
    Returns:
        List of (rank, suit) tuples
    """
    return [(CARD_ID_TO_RANK[i], CARD_ID_TO_SUIT[i]) for i in card_ids]

def id_to_rank(card_id):
    """Convert single card ID to rank"""
    return CARD_ID_TO_RANK[card_id]

def id_to_suit(card_id):
    """Convert single card ID to suit"""
    return CARD_ID_TO_SUIT[card_id]

def id_to_value(card_id):
    """Convert single card ID to comparison value"""
    return CARD_ID_TO_VALUE[card_id]

# ============================================================================
# String Conversion Functions
# ============================================================================

def cards2str_ids(card_ids):
    """
    Convert card IDs to string representation
    
    Args:
        card_ids: List of card IDs
        
    Returns:
        String representation (e.g., '3456789TJQKA2BJRJ')
    """
    ranks = ids_to_ranks(card_ids)
    return "".join(ranks)

def str_to_cards_ids(card_str):
    """
    Convert string representation to card IDs
    
    Args:
        card_str: String of ranks (e.g., '33344')
        
    Returns:
        List of card IDs (chooses first available cards)
    """
    card_ids = []
    for rank in card_str:
        # Find first available card with this rank
        for i, r in enumerate(CARD_ID_TO_RANK):
            if r == rank and i not in card_ids:
                card_ids.append(i)
                break
    return card_ids

def cards_to_ids(card_str):
    """
    Alias for str_to_cards_ids for compatibility with env
    
    Args:
        card_str: String of ranks (e.g., '33344')
        
    Returns:
        List of card IDs
    """
    return str_to_cards_ids(card_str)

# ============================================================================
# Card Type Detection
# ============================================================================

def is_consecutive(values, min_length=5):
    """
    Check if values are consecutive (for straight detection)
    
    Args:
        values: List of integer values
        min_length: Minimum length for consecutive sequence
        
    Returns:
        bool: True if consecutive
    """
    if len(values) < min_length:
        return False
    
    sorted_vals = sorted(set(values))
    if len(sorted_vals) != len(values):
        return False  # Contains duplicates
    
    return all(sorted_vals[i+1] - sorted_vals[i] == 1 for i in range(len(sorted_vals)-1))

def is_same_suit(suits):
    """
    Check if all cards have the same suit
    
    Args:
        suits: List of suit strings
        
    Returns:
        bool: True if same suit
    """
    return len(set(suits)) == 1

def count_ranks_with_wildcard(ranks, wildcard_rank):
    """
    Count ranks considering wildcards
    
    Args:
        ranks: List of rank strings
        wildcard_rank: Current level card that can be used as wildcards
        
    Returns:
        dict: Rank to count mapping (wildcards counted separately)
    """
    rank_counts = {}
    wildcard_count = 0
    
    for rank in ranks:
        if rank == wildcard_rank:
            wildcard_count += 1
        else:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    # Add wildcard info
    if wildcard_count > 0:
        rank_counts['__wildcards'] = wildcard_count
    
    return rank_counts

def detect_card_type(card_ids, level_rank='2'):
    """
    Detect card type dynamically (supports straight flush, bombs with wildcards, etc.)
    
    Args:
        card_ids: List of card IDs
        level_rank: Current level rank that can act as wildcard (e.g., '2')
        
    Returns:
        dict: Card type information
        {
            'type': 'straight_flush' | 'bomb' | 'straight' | 'pair' | 'triple' | ...
            'rank': 900-1000 for special types, 0-700 for normal types
            'main_value': Main card value for comparison
            'is_wildcard_used': True if wildcards were used
        }
    """
    if not card_ids or len(card_ids) == 0:
        return {'type': 'invalid', 'rank': -1}
    
    # Convert to ranks, suits, and values
    ranks = ids_to_ranks(card_ids)
    suits = ids_to_suits(card_ids)
    values = ids_to_values(card_ids)
    
    # Count ranks (considering wildcards)
    rank_counts = count_ranks_with_wildcard(ranks, level_rank)
    wildcard_count = rank_counts.get('__wildcards', 0)
    
    # Remove wildcard entry for processing
    if '__wildcards' in rank_counts:
        del rank_counts['__wildcards']
    
    # Sort by frequency and value
    sorted_counts = sorted(rank_counts.items(), 
                          key=lambda x: (x[1], RANK_TO_VALUE[x[0]]), 
                          reverse=True)
    
    # Determine card type based on counts
    max_count = sorted_counts[0][1] if sorted_counts else 0
    num_cards = len(card_ids)
    
    # 1. Check for joker bomb (both jokers)
    if set(ranks) == {'BJ', 'RJ'} and len(card_ids) == 2:
        return {
            'type': 'joker_bomb',
            'rank': 1000,
            'main_value': 14,
            'is_wildcard_used': False
        }
    
    # 2. Check for straight flush (5+ consecutive same suit)
    if num_cards >= 5 and is_same_suit(suits) and is_consecutive(values):
        return {
            'type': 'straight_flush',
            'rank': 950 + max(values),
            'main_value': max(values),
            'is_wildcard_used': (wildcard_count > 0)
        }
    
    # 3. Check for bomb (4+ of same rank, with wildcards)
    if max_count + wildcard_count >= 4 and sorted_counts:
        main_rank = sorted_counts[0][0]
        bomb_size = max_count + wildcard_count
        
        # Only bombs of size 4-8 are valid
        if 4 <= bomb_size <= 8:
            return {
                'type': f'bomb_{bomb_size}',
                'rank': 800 + bomb_size * 10 + RANK_TO_VALUE[main_rank],
                'main_value': RANK_TO_VALUE[main_rank],
                'is_wildcard_used': (wildcard_count > 0)
            }
    
    # 4. Check for straight (5+ consecutive, different suits)
    if num_cards >= 5 and not is_same_suit(suits) and is_consecutive(values):
        return {
            'type': 'straight',
            'rank': 700 + max(values),
            'main_value': max(values),
            'is_wildcard_used': (wildcard_count > 0)
        }
    
    # 5. Detect other types based on pattern
    if num_cards == 1:
        return {
            'type': 'solo',
            'rank': RANK_TO_VALUE[ranks[0]],
            'main_value': RANK_TO_VALUE[ranks[0]],
            'is_wildcard_used': (wildcard_count > 0)
        }
    
    elif num_cards == 2 and max_count == 2:
        return {
            'type': 'pair',
            'rank': RANK_TO_VALUE[sorted_counts[0][0]],
            'main_value': RANK_TO_VALUE[sorted_counts[0][0]],
            'is_wildcard_used': (wildcard_count > 0)
        }
    
    elif num_cards == 3 and max_count == 3:
        return {
            'type': 'triple',
            'rank': RANK_TO_VALUE[sorted_counts[0][0]],
            'main_value': RANK_TO_VALUE[sorted_counts[0][0]],
            'is_wildcard_used': (wildcard_count > 0)
        }
    
    # 6. Full house (triple + pair)
    elif num_cards == 5 and max_count == 3 and len(sorted_counts) >= 2 and sorted_counts[1][1] == 2:
        return {
            'type': 'full_house',
            'rank': 600 + RANK_TO_VALUE[sorted_counts[0][0]],
            'main_value': RANK_TO_VALUE[sorted_counts[0][0]],
            'is_wildcard_used': (wildcard_count > 0)
        }
    
    # 7. Four cards with single (triple + single)
    elif num_cards == 4 and max_count == 3:
        return {
            'type': 'triple_solo',
            'rank': 500 + RANK_TO_VALUE[sorted_counts[0][0]],
            'main_value': RANK_TO_VALUE[sorted_counts[0][0]],
            'is_wildcard_used': (wildcard_count > 0)
        }
    
    # 8. Tube (consecutive pairs, 3+ pairs)
    # 9. Plate (consecutive triples, 2+ triples)
    # ... additional patterns to be implemented
    
    return {
        'type': 'invalid',
        'rank': -1,
        'main_value': -1,
        'is_wildcard_used': False
    }

# ============================================================================
# Card Comparison Utilities
# ============================================================================

def can_beat(card_ids_a, card_ids_b, level_rank='2'):
    """
    Check if cards_a can beat cards_b
    
    Args:
        card_ids_a: Cards to play
        card_ids_b: Cards to beat
        level_rank: Current level rank
        
    Returns:
        bool: True if card_ids_a can beat card_ids_b
    """
    if not card_ids_b:  # Free to play anything
        return True
    
    type_a = detect_card_type(card_ids_a, level_rank)
    type_b = detect_card_type(card_ids_b, level_rank)
    
    if type_a['type'] == 'invalid':
        return False
    
    # Special types comparison
    if type_a['rank'] >= 800 or type_b['rank'] >= 800:  # Bombs or special
        return type_a['rank'] > type_b['rank']
    
    # Same type comparison
    if type_a['type'] == type_b['type'] and card_ids_a == card_ids_b:
        return type_a['main_value'] > type_b['main_value']
    
    return False

def contains_cards(hand_ids, target_ids, level_rank='2'):
    """
    Check if hand contains target cards (considering wildcards)
    
    Args:
        hand_ids: Player's hand
        target_ids: Cards to check
        level_rank: Current level rank
        
    Returns:
        bool: True if hand contains target
    """
    if not target_ids:
        return True
    
    hand_ranks = ids_to_ranks(hand_ids)
    target_ranks = ids_to_ranks(target_ids)
    
    hand_counts = count_ranks_with_wildcard(hand_ranks, level_rank)
    target_counts = count_ranks_with_wildcard(target_ranks, level_rank)
    
    # Remove wildcard entry
    hand_wildcards = hand_counts.get('__wildcards', 0)
    if '__wildcards' in hand_counts:
        del hand_counts['__wildcards']
    target_wildcards = target_counts.get('__wildcards', 0)
    if '__wildcards' in target_counts:
        del target_counts['__wildcards']
    
    # Check if we can cover target with hand cards + wildcards
    wildcards_needed = 0
    for rank, count in target_counts.items():
        hand_count = hand_counts.get(rank, 0)
        if hand_count < count:
            wildcards_needed += (count - hand_count)
    
    return wildcards_needed <= hand_wildcards

# Pre-compute straight flush patterns for fast detection
STRAIGHT_FLUSH_PATTERNS = []
for start_value in range(0, 10):  # 3 to A (5-card minimum)
    pattern = list(range(start_value, start_value + 5))
    STRAIGHT_FLUSH_PATTERNS.append(set(pattern))

def is_straight_flush_fast(card_ids):
    """
    Fast straight flush detection using set operations
    
    Args:
        card_ids: List of card IDs
        
    Returns:
        bool: True if straight flush
    """
    if len(card_ids) < 5:
        return False
    
    suits = ids_to_suits(card_ids)
    if not is_same_suit(suits):
        return False
    
    values = set(ids_to_values(card_ids))
    for pattern in STRAIGHT_FLUSH_PATTERNS:
        if pattern.issubset(values):
            return True
    
    return False
