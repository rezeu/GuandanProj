"""
Player class for Guandan v2
Supports structured actions and tracks played cards
"""

from rlcard.games.guandan_v2.card_utils import contains_cards, ids_to_ranks
from rlcard.games.guandan_v2.action import GuandanAction

class GuandanPlayer:
    """Player class for Guandan game"""
    
    def __init__(self, player_id, np_random):
        """
        Initialize player
        
        Args:
            player_id: Unique player ID (0-3)
            np_random: Random number generator
        """
        self.np_random = np_random
        self.player_id = player_id
        self.current_hand = []  # Card IDs in hand
        self.initial_hand = ""  # String representation
        self.played_cards = []  # Cards played in current round
        self._recorded_played_cards = []  # History of played cards
        self.last_action = None  # Last action taken
        
    def set_current_hand(self, hand_ids):
        """Set current hand (list of card IDs)"""
        self.current_hand = sorted(hand_ids)
    
    def get_state(self, public, others_hand, num_cards_left, actions):
        """
        Get player's state
        
        Args:
            public: Public game information
            others_hand: Opponents' hands
            num_cards_left: Cards left for each player
            actions: Legal actions
            
        Returns:
            dict: Player state
        """
        state = {}
        state['current_hand'] = self.current_hand
        state['others_hand'] = others_hand
        state['num_cards_left'] = num_cards_left
        state['actions'] = actions
        state['trace'] = public['trace']
        state['played_cards'] = public['played_cards']
        state['self'] = self.player_id
        
        return state
    
    def available_actions(self, greater_player, judger):
        """
        Get available actions
        
        Args:
            greater_player: Player to beat, or None
            judger: Judger for validation
            
        Returns:
            list: Available GuandanAction objects
        """
        actions = judger.get_legal_actions(self, greater_player)
        return actions
    
    def play(self, action, greater_player=None):
        """
        Play action
        
        Args:
            action: GuandanAction to play
            greater_player: Player to beat, or None
            
        Returns:
            self if action is successful, or greater_player if pass
        """
        # Handle pass
        if action.is_pass():
            self._recorded_played_cards.append([])
            self.last_action = action
            return greater_player
        
        # Check that action is valid
        if not contains_cards(self.current_hand, action.actual_ids, action.level_rank):
            raise ValueError(f"Player {self.player_id}: Cards not in hand")
        
        # Remove cards from hand
        self._remove_cards_from_hand(action.actual_ids, action.level_rank)
        
        # Record played cards
        self.played_cards = action.claim_ids
        self._recorded_played_cards.append(action.actual_ids)
        self.last_action = action
        
        return self
    
    def _remove_cards_from_hand(self, card_ids, level_rank):
        """
        Remove cards from hand using wildcard logic
        
        Args:
            card_ids: Cards to remove
            level_rank: Current level rank (used as wildcard)
        """
        # Make a copy to avoid modifying while iterating
        remaining_hand = self.current_hand.copy()
        
        for card_id in card_ids:
            if card_id in remaining_hand:
                remaining_hand.remove(card_id)
            else:
                # Try to use wildcard (level card)
                wildcards = [cid for cid in remaining_hand if id_to_rank(cid) == level_rank]
                if wildcards:
                    remaining_hand.remove(wildcards[0])
                else:
                    raise ValueError(f"Card {card_id} not found in hand")
        
        self.current_hand = remaining_hand
    
    def get_player_id(self):
        """Get player ID"""
        return self.player_id
    
    @property
    def hand_size(self):
        """Get number of cards in hand"""
        return len(self.current_hand)

def id_to_rank(card_id):
    """Helper to get rank from ID"""
    from rlcard.games.guandan_v2.card_utils import id_to_rank as get_rank
    return get_rank(card_id)

def id_to_value(card_id):
    """Helper to get value from ID"""
    from rlcard.games.guandan_v2.card_utils import id_to_value as get_value
    return get_value(card_id)