"""
Dealer for Guandan v2
Deals cards and manages deck using card IDs
"""

import numpy as np
from rlcard.utils import init_108_deck
from rlcard.games.guandan_v2.card_utils import cards2str_ids, RANK_TO_VALUE, RANK_ORDER, SUIT_ORDER

class GuandanDealer:
    """Dealer for Guandan game - 4 players, 108 cards"""
    
    def __init__(self, np_random):
        """Initialize dealer with 108-card deck"""
        self.np_random = np_random
        self.deck = init_108_deck()  # Returns list of Card objects
        self.deck_ids = self._cards_to_ids(self.deck)  # Convert to IDs
        self.deck_ids.sort()  # Sort for consistency
        
        # Validate uniqueness
        if len(self.deck_ids) != len(set(self.deck_ids)):
            raise ValueError("Duplicate card IDs detected in deck!")
        
    def _cards_to_ids(self, cards):
        """Convert Card objects to card IDs (0-107)"""
        ids = []
        for idx, card in enumerate(cards):
            if card.rank == '':  # Joker case
                rank = card.suit  # 'BJ' or 'RJ'
                suit = card.suit  # 'BJ' or 'RJ'
            else:
                rank = card.rank
                suit = card.suit
            
            # Find card ID based on position in deck
            id_val = self._find_card_id(rank, suit, idx)
            ids.append(id_val)
        
        return ids
    
    def _find_card_id(self, rank, suit, position):
        """Find card ID (0-107) based on rank, suit, and position in deck"""
        # Position < 54: first deck (ID 0-53)
        # Position >= 54: second deck (ID 54-107)
        deck_offset = 0 if position < 54 else 54
        
        # Size-specific mapping
        if rank in ['BJ', 'RJ']:
            # Jokers: first deck positions 52-53, second deck 106-107
            return deck_offset + (52 if rank == 'BJ' else 53)
        
        # Regular cards (3-2, A, K, Q, J, T)
        # Map suit symbols: S->♠, H->♥, D->♦, C->♣
        suit_map = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
        if suit in suit_map:
            suit = suit_map[suit]
        
        # Use RANK_TO_VALUE from card_utils
        if rank not in RANK_TO_VALUE:
            raise ValueError(f"Invalid rank: {rank}")
        
        if suit not in SUIT_ORDER:
            raise ValueError(f"Invalid suit: {suit}")
        
        rank_value = RANK_TO_VALUE[rank]  # 0-14
        suit_value = SUIT_ORDER[suit]     # 0-3 for suits
        
        # For regular cards (not jokers):
        # ID = deck_offset + suit_value * 13 + rank_value
        # where rank_value is position in RANK_ORDER (0-12 for 3-2)
        if rank_value <= 12:  # 3, 4, 5, 6, 7, 8, 9, T, J, Q, K, A, 2
            return deck_offset + suit_value * 13 + rank_value
        else:
            # Should not happen for regular cards
            raise ValueError(f"Invalid rank for regular card: {rank}")
    
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
            
            # Validate no duplicates in this player's hand
            if len(player_hand) != len(set(player_hand)):
                raise ValueError(f"Duplicate cards in player {i}'s hand!")
    
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