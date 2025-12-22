"""
Judger for Guandan v2
Validates card plays and determines legal actions with wildcard support
"""

from rlcard.games.guandan_v2.card_utils import (
    detect_card_type, contains_cards, ids_to_ranks,
    RANK_TO_VALUE
)
from rlcard.games.guandan_v2.action import GuandanAction

class GuandanJudger:
    """Judger for Guandan game - validates actions and determines legal plays"""
    
    def __init__(self, level_rank='2'):
        """
        Initialize judger
        
        Args:
            level_rank: Current level rank that acts as wildcard (default: '2')
        """
        self.level_rank = level_rank
    
    def set_level_rank(self, level_rank):
        """Update level rank (used when players level up)"""
        self.level_rank = level_rank
    
    def get_legal_actions(self, player, greater_player=None):
        """
        Get all legal actions for a player
        
        Args:
            player: GuandanPlayer object
            greater_player: Player who played current highest cards, or None
            
        Returns:
            list: Legal GuandanAction objects
        """
        hand_ids = player.current_hand
        
        if greater_player is None or greater_player.player_id == player.player_id:
            # No cards to beat - can play anything
            return self._get_all_playable_actions(hand_ids)
        else:
            # Need to beat greater player's cards
            greater_action = greater_player.last_action
            return self._get_beat_actions(hand_ids, greater_action)
    
    def _get_all_playable_actions(self, hand_ids):
        """Get all playable actions from hand (no restriction)"""
        actions = [GuandanAction([], [], 'pass', self.level_rank)]
        
        # Get all possible card combinations
        combinations = self._generate_card_combinations(hand_ids)
        
        for combo in combinations:
            # For each combo, detect its type
            type_info = detect_card_type(combo, self.level_rank)
            if type_info['type'] != 'invalid':
                action = GuandanAction(combo, combo, type_info['type'], self.level_rank)
                actions.append(action)
        
        return actions
    
    def _get_beat_actions(self, hand_ids, greater_action):
        """Get actions that can beat greater_action"""
        actions = [GuandanAction([], [], 'pass', self.level_rank)]
        
        if greater_action is None or greater_action.is_pass():
            return self._get_all_playable_actions(hand_ids)
        
        # Get all possible combinations
        combinations = self._generate_card_combinations(hand_ids)
        
        for combo in combinations:
            if self._can_beat(combo, greater_action):
                type_info = detect_card_type(combo, self.level_rank)
                action = GuandanAction(combo, combo, type_info['type'], self.level_rank)
                actions.append(action)
        
        return actions
    
    def _can_beat(self, combo_ids, greater_action):
        """Check if combo can beat greater_action"""
        combo_type = detect_card_type(combo_ids, self.level_rank)
        greater_type = detect_card_type(greater_action.claim_ids, self.level_rank)
        
        if combo_type['type'] == 'invalid':
            return False
        
        # Special types (bombs, straight flushes) can beat anything lower
        if combo_type['rank'] >= 800 or greater_type['rank'] >= 800:
            return combo_type['rank'] > greater_type['rank']
        
        # Same type with same length
        if (combo_type['type'] == greater_type['type'] and 
            len(combo_ids) == len(greater_action.claim_ids)):
            return combo_type['main_value'] > greater_type['main_value']
        
        return False
    
    def _generate_card_combinations(self, hand_ids):
        """
        Generate all valid card combinations from hand
        
        Args:
            hand_ids: List of card IDs in hand
            
        Returns:
            List of card ID combinations
        """
        combinations = []
        n = len(hand_ids)
        
        # Generate combinations of various sizes
        # 1. Single cards
        for i in range(n):
            combinations.append([hand_ids[i]])
        
        # 2. Pairs (2 cards)
        from collections import Counter
        ranks = ids_to_ranks(hand_ids)
        rank_counts = Counter(ranks)
        
        for rank, count in rank_counts.items():
            if count >= 2:
                # Find all cards with this rank
                rank_cards = [cid for cid in hand_ids if id_to_rank(cid) == rank]
                combinations.append(rank_cards[:2])
        
        # 3. Triples (3 cards)
        for rank, count in rank_counts.items():
            if count >= 3:
                rank_cards = [cid for cid in hand_ids if id_to_rank(cid) == rank]
                combinations.append(rank_cards[:3])
        
        # 4. Bombs (4+ cards of same rank)
        for rank, count in rank_counts.items():
            if count >= 4:
                rank_cards = [cid for cid in hand_ids if id_to_rank(cid) == rank]
                for bomb_size in range(4, min(count, 8) + 1):
                    combinations.append(rank_cards[:bomb_size])
        
        # 5. Straights (5+ consecutive cards)
        straights = self._find_straights(hand_ids)
        combinations.extend(straights)
        
        # 6. Full houses, tubes, plates (to be implemented)
        # For now, we'll use a simplified approach without considering wildcards
        
        return combinations
    
    def _find_straights(self, hand_ids):
        """Find all valid straights in hand"""
        straights = []
        values = sorted(set([id_to_value(cid) for cid in hand_ids]))
        
        # Need at least 5 cards for straight
        if len(values) < 5:
            return straights
        
        # Find all consecutive sequences
        for length in range(5, len(values) + 1):
            for start in range(0, len(values) - length + 1):
                sequence = values[start:start + length]
                if self._is_consecutive(sequence):
                    # Convert back to cards (simplified: use first available)
                    straight_cards = []
                    for val in sequence:
                        card = [cid for cid in hand_ids if id_to_value(cid) == val][0]
                        straight_cards.append(card)
                    straights.append(straight_cards)
        
        return straights
    
    def _is_consecutive(self, values):
        """Check if values are consecutive"""
        return all(values[i+1] - values[i] == 1 for i in range(len(values)-1))
    
    def validate_play(self, action, player, greater_player):
        """
        Validate if a play is legal
        
        Args:
            action: GuandanAction to validate
            player: Player making the play
            greater_player: Player to beat, or None
            
        Returns:
            bool: True if play is valid
        """
        if action.is_pass():
            return True
        
        # Check action is in player's hand
        if not contains_cards(player.current_hand, action.actual_ids, self.level_rank):
            return False
        
        # Check action type is valid
        type_info = detect_card_type(action.actual_ids, self.level_rank)
        if type_info['type'] == 'invalid':
            return False
        
        # Check if we need to beat someone
        if greater_player and greater_player.last_action:
            return self._can_beat(action.actual_ids, greater_player.last_action)
        
        return True

def id_to_rank(card_id):
    """Get rank from card ID"""
    from rlcard.games.guandan_v2.card_utils import id_to_rank as get_rank
    return get_rank(card_id)

def id_to_value(card_id):
    """Get comparison value from card ID"""
    from rlcard.games.guandan_v2.card_utils import id_to_value as get_value
    return get_value(card_id)
