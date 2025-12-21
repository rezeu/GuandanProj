"""
Dealer for Guandan v2
Deals cards and manages deck using card IDs
"""

import numpy as np
from rlcard.utils import init_108_deck
from rlcard.games.guandan_v2.card_utils import cards2str_ids

class GuandanDealer:
    """Dealer for Guandan game - 4 players, 108 cards"""
    
    def __init__(self, np_random):
        """Initialize dealer with 108-card deck"""
        self.np_random = np_random
        self.deck = init_108_deck()  # Returns list of Card objects
        self.deck_ids = self._cards_to_ids(self.deck)  # Convert to IDs
        self.deck_ids.sort()  # Sort for consistency
        
    def _cards_to_ids(self, cards):
        """Convert Card objects to card IDs"""
        # Map from Card's rank+suit to ID
        # Card(rank='3', suit='♥') -> 0
        # Card(rank='BJ', suit='BJ') -> 26 (first deck)
        # Card(rank='BJ', suit='BJ') -> 80 (second deck)
        
        ids = []
        for card in cards:
            if card.rank == '':  # Joker case
                rank = card.suit
                suit = card.suit
            else:
                rank = card.rank
                suit = card.suit
            
            # Find matching ID
            id_val = self._find_card_id(rank, suit, len(ids))
            ids.append(id_val)
        
        return ids
    
    def _find_card_id(self, rank, suit, position):
        """Find card ID based on rank and suit"""
        # Use position to determine which deck (0-53 for first, 54-107 for second)
        deck_offset = 0 if position < 54 else 54
        
        # Map suit to offset within deck
        suit_order = {'♥': 0, '♦': 1, '♣': 2, '♠': 3, 'BJ': 4, 'RJ': 4}
        rank_order = {'3': 0, '4': 1, '5': 2, '6': 3, '7': 4, '8': 5, '9': 6, 
                     'T': 7, 'J': 8, 'Q': 9, 'K': 10, 'A': 11, '2': 12, 
                     'BJ': 13, 'RJ': 14}
        
        if rank in ['BJ', 'RJ']:
            # Jokers have special handling
            if rank == 'BJ':
                return deck_offset + 52  # BJ position
            else:
                return deck_offset + 53  # RJ position
        
        # Regular cards
        suit_offset = suit_order.get(suit, 0) * 13
        rank_offset = rank_order.get(rank, 0)
        return deck_offset + suit_offset + rank_offset
    
    def shuffle(self):
        """Shuffle the deck"""
        self.np_random.shuffle(self.deck_ids)
    
    def deal_cards(self, players):
        """
        Deal cards to 4 players (27 cards each)
        
        Args:
            players: List of 4 GuandanPlayer objects
        """
        assert len(players) == 4, "Guandan requires exactly 4 players"
        
        self.shuffle()
        
        # Deal 27 cards to each player
        cards_per_player = len(self.deck_ids) // len(players)
        
        for i, player in enumerate(players):
            start_idx = i * cards_per_player
            end_idx = (i + 1) * cards_per_player
            player_hand = self.deck_ids[start_idx:end_idx]
            player_hand.sort()  # Sort for consistency
            
            player.set_current_hand(player_hand)
            player.initial_hand = cards2str_ids(player_hand)
    
    def determine_role(self, players):
        """
        Determine starting player for Guandan
        
        Args:
            players: List of 4 GuandanPlayer objects
            
        Returns:
            int: Starting player ID (always 0 for simplicity)
        """
        # Deal cards
        self.deal_cards(players)
        
        # In Guandan, game starts with player 0
        return 0
