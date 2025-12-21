"""
Action class for Guandan v2
Supports structured actions with actual cards and wildcard claims
"""

from rlcard.games.guandan_v2.card_utils import (
    ids_to_ranks, contains_cards, detect_card_type, RANK_TO_VALUE,
    id_to_rank
)

class GuandanAction:
    """
    Structured action representing card play with potential wildcard usage
    
    Attributes:
        actual_ids: List of card IDs actually played from hand
        claim_ids: List of card IDs representing the claimed pattern
        claim_type: String type of the claimed pattern (e.g., 'full_house')
        wildcards_used: Dict mapping actual wildcard IDs to claimed rank
    """
    
    def __init__(self, actual_ids, claim_ids, claim_type, level_rank='2'):
        """
        Initialize a Guandan action
        
        Args:
            actual_ids: List of card IDs actually played
            claim_ids: List of card IDs representing claimed pattern
            claim_type: Type of the claimed pattern
            level_rank: Current level rank that acts as wildcard
        """
        self.actual_ids = sorted(actual_ids) if actual_ids else []
        self.claim_ids = sorted(claim_ids) if claim_ids else []
        self.claim_type = claim_type
        self.level_rank = level_rank
        self.wildcards_used = {}
        
        # Detect which cards are wildcards
        self._identify_wildcards()
    
    def _identify_wildcards(self):
        """Identify which cards in actual are wildcards used for claim"""
        actual_ranks = ids_to_ranks(self.actual_ids)
        claim_ranks = ids_to_ranks(self.claim_ids)
        
        # Count occurrences of each rank
        from collections import Counter
        actual_counts = Counter(actual_ranks)
        claim_counts = Counter(claim_ranks)
        
        # Wildcards are level cards used to fill gaps
        wildcard_available = actual_counts.get(self.level_rank, 0)
        wildcards_needed = 0
        
        for rank, claim_count in claim_counts.items():
            actual_count = actual_counts.get(rank, 0)
            if actual_count < claim_count:
                wildcards_needed += (claim_count - actual_count)
        
        # Map wildcards to claimed ranks
        if wildcards_needed > 0 and wildcard_available >= wildcards_needed:
            wildcard_id_idx = 0
            for i, card_id in enumerate(self.actual_ids):
                if id_to_rank(card_id) == self.level_rank:
                    # Find which rank this wildcard is claiming
                    for rank, claim_count in claim_counts.items():
                        actual_count = actual_counts.get(rank, 0)
                        if actual_count < claim_count:
                            self.wildcards_used[card_id] = rank
                            actual_counts[rank] = actual_counts.get(rank, 0) + 1
                            actual_counts[self.level_rank] -= 1
                            break
    
    def is_pass(self):
        """Check if this action is a pass"""
        return len(self.actual_ids) == 0 and len(self.claim_ids) == 0
    
    def validate(self, hand_ids):
        """
        Validate that this action is legal given the hand
        
        Args:
            hand_ids: List of card IDs in player's hand
            
        Returns:
            bool: True if action is valid
        """
        if self.is_pass():
            return True
        
        # Check that actual cards are in hand
        if not contains_cards(hand_ids, self.actual_ids, self.level_rank):
            return False
        
        # Check that actual cards can form claimed pattern
        return self._can_form_pattern()
    
    def _can_form_pattern(self):
        """Check if actual cards can form claimed pattern"""
        if len(self.actual_ids) != len(self.claim_ids):
            return False
        
        # Get the card type of claim
        claim_type_info = detect_card_type(self.claim_ids, self.level_rank)
        if claim_type_info['type'] != self.claim_type:
            return False
        
        # Check if we can transform actual to claim using wildcards
        return self._check_wildcard_transform()
    
    def _check_wildcard_transform(self):
        """Check if actual cards can be transformed to claim using wildcards"""
        # This is simplified - full implementation would check all possibilities
        actual_ranks = ids_to_ranks(self.actual_ids)
        claim_ranks = ids_to_ranks(self.claim_ids)
        
        # With enough wildcards, any transformation is possible
        wildcard_count = actual_ranks.count(self.level_rank)
        
        # Check rank distributions match when considering wildcards
        from collections import Counter
        actual_counts = Counter(actual_ranks)
        claim_counts = Counter(claim_ranks)
        
        # Remove wildcards from actual
        if self.level_rank in actual_counts:
            del actual_counts[self.level_rank]
        
        # Check if actual + wildcards can form claim
        for rank, claim_count in claim_counts.items():
            actual_count = actual_counts.get(rank, 0)
            if actual_count > claim_count:
                return False  # Too many of this rank
            elif actual_count < claim_count:
                # Need wildcards to make up the difference
                needed = claim_count - actual_count
                if wildcard_count < needed:
                    return False
                wildcard_count -= needed
        
        return True
    
    def to_string(self):
        """Convert action to string representation for display"""
        if self.is_pass():
            return "pass"
        
        actual_str = "".join(ids_to_ranks(self.actual_ids))
        claim_str = "".join(ids_to_ranks(self.claim_ids))
        
        if self.wildcards_used:
            wildcard_info = f" (wildcards: {len(self.wildcards_used)})"
        else:
            wildcard_info = ""
        
        if actual_str == claim_str:
            return f"{claim_str}{wildcard_info}"
        else:
            return f"{actual_str}->{claim_str}{wildcard_info}"
    
    def to_action_id(self, action_space=None):
        """
        Convert to action ID for environment
        Uses dynamic ID based on card IDs for combination games
        
        Args:
            action_space: Ignored for compatibility, dynamically calculates ID
            
        Returns:
            int: Action ID (0 for pass, hash-based for others)
        """
        if self.is_pass():
            return 0
        
        # For other actions, create a deterministic ID based on claim_ids
        # Use a simple hash: sum of claim_ids + type-based offset
        base_id = sum(self.claim_ids) if self.claim_ids else 0
        
        # Add type-based offset to avoid collisions between different types
        type_offsets = {
            'solo': 100,
            'pair': 1000,
            'triple': 2000,
            'straight': 3000,
            'straight_flush': 4000,
            'bomb_4': 5000,
            'bomb_5': 6000,
            'bomb_6': 7000,
            'bomb_7': 8000,
            'bomb_8': 9000,
            'joker_bomb': 10000
        }
        
        # Detect type if not set
        if not hasattr(self, 'claim_type') or not self.claim_type:
            from rlcard.games.guandan_v2.card_utils import detect_card_type
            type_info = detect_card_type(self.actual_ids, self.level_rank)
            self.claim_type = type_info['type']
        
        offset = type_offsets.get(self.claim_type, 500)
        action_id = base_id + offset
        
        # Ensure action_id fits in action_shape [400] range
        return action_id % 400
    
    @classmethod
    def from_string(cls, action_str, hand_ids, level_rank='2'):
        """
        Parse action from string format
        
        Args:
            action_str: String like "33344" or "pass"
            hand_ids: Player's hand for validation
            level_rank: Current level rank
            
        Returns:
            GuandanAction instance
        """
        if action_str == 'pass':
            return cls([], [], 'pass', level_rank)
        
        # Simple case: actual == claim
        actual_ids = [rank_to_id(rank) for rank in action_str]
        claim_ids = actual_ids.copy()
        
        # Detect type
        type_info = detect_card_type(claim_ids, level_rank)
        
        return cls(actual_ids, claim_ids, type_info['type'], level_rank)

# Helper function

def rank_to_id(rank, suit='♥'):
    """Convert rank string to card ID (simplified, returns first match)"""
    for i, r in enumerate(CARD_ID_TO_RANK):
        if r == rank:
            return i
    return -1  # Not found

def create_action(actual_ids, claimed_pattern, level_rank='2'):
    """
    Factory function to create GuandanAction
    
    Args:
        actual_ids: Cards from hand
        claimed_pattern: The pattern trying to form (e.g., '33344')
        level_rank: Current level rank
        
    Returns:
        GuandanAction
    """
    from rlcard.games.guandan_v2.card_utils import cards_to_ids
    
    claim_ids = cards_to_ids(claimed_pattern)
    
    # Detect type from claim
    type_info = detect_card_type(claim_ids, level_rank)
    
    return GuandanAction(actual_ids, claim_ids, type_info['type'], level_rank)

def cards_to_ids(card_str):
    """Convert card string to ID list"""
    return [rank_to_id(rank) for rank in card_str]

def is_valid_play(hand_ids, action, greater_action, level_rank='2'):
    """
    Check if action is valid compared to greater action
    
    Args:
        hand_ids: Player's hand
        action: Current action (GuandanAction)
        greater_action: Previous action to beat (GuandanAction)
        level_rank: Current level rank
        
    Returns:
        bool: True if valid play
    """
    if action.is_pass():
        return True
    
    # Check action is in hand
    if not action.validate(hand_ids):
        return False
    
    # If no greater action to beat, any valid action is fine
    if greater_action is None or greater_action.is_pass():
        return True
    
    # Check if we can beat greater action
    return can_beat(action.claim_ids, greater_action.claim_ids, level_rank)