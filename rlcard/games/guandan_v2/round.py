"""
Round class for Guandan v2 - NEW FILE
Manages turn order including wind-taking rule (接风)
"""

import numpy as np
from rlcard.games.guandan_v2.dealer import GuandanDealer
from rlcard.games.guandan_v2.card_utils import cards2str_ids

class GuandanRound:
    """
    Round manages the game flow including:
    - Card dealing
    - Turn order
    - Wind-taking rule (接风)
    - Play tracking
    """
    
    def __init__(self, np_random, played_cards):
        """
        Initialize round
        
        Args:
            np_random: Random number generator
            played_cards: Tracking of played cards for each player
        """
        self.np_random = np_random
        self.played_cards = played_cards
        self.trace = []  # Action history: [(player_id, action), ...]
        self.greater_player = None
        self.dealer = GuandanDealer(self.np_random)
        self.deck_ids = self.dealer.deck_ids.copy()
        
        # Wind-taking (接风) tracking
        self.consecutive_passes = 0
        self.last_played_player = None  # Last player who successfully played cards
        
    def initiate(self, players):
        """
        Initialize game round
        
        Args:
            players: List of 4 GuandanPlayer objects
            
        Returns:
            Starting player ID
        """
        # Store players reference
        self.players = players
        
        # Deal cards
        starting_player = self.dealer.determine_role(players)
        
        # Initialize game state
        self.seen_cards = ''  # Guandan doesn't have seen cards like DouDizhu
        self.current_player = starting_player
        self.last_played_player = starting_player
        
        # Public game state (visible to all)
        self.public = {
            'deck': cards2str_ids(self.deck_ids),
            'seen_cards': self.seen_cards,
            'trace': self.trace,
            'played_cards': ['' for _ in range(len(players))]
        }
        
        return starting_player
    
    def proceed_round(self, players, action):
        """
        Proceed to next round with action
        
        Args:
            players: List of players
            action: GuandanAction taken by current player
            
        Returns:
            next_player_id: ID of next player to play
        """
        current_player = players[self.current_player]
        
        # Record action in trace
        self.trace.append((self.current_player, action))
        
        # Update public played cards
        if not action.is_pass():
            self.public['played_cards'][self.current_player] = cards2str_ids(action.actual_ids)
        
        # Process the action
        greater_player = current_player.play(action, self.greater_player)
        
        if action.is_pass():
            # Handle pass - increment consecutive pass counter
            self.consecutive_passes += 1
            
            # Check if all other players have passed (3 consecutive passes)
            if self.consecutive_passes >= 3:
                # Wind-taking rule: next turn goes to last played player's teammate
                # 确保last_played_player已设置
                if self.last_played_player is not None:
                    next_player = self._apply_wind_taking_rule()
                else:
                    # 不应该发生，但回退到正常轮转
                    next_player = self._get_next_player(self.current_player)
                self.consecutive_passes = 0
                self.greater_player = None
            else:
                # Normal rotation
                next_player = self._get_next_player(self.current_player)
        else:
            # Player successfully played cards
            self.consecutive_passes = 0
            self.greater_player = greater_player
            # 更新last_played_player（关键：记录上一成功出牌的玩家）
            self.last_played_player = self.current_player
            next_player = self._get_next_player(self.current_player)
        
        # Update current player
        self.current_player = next_player
        return next_player
    
    def _apply_wind_taking_rule(self):
        """
        Apply wind-taking rule (接风)
        When all 3 other players pass, next turn goes to teammate of last player who played
        
        Returns:
            int: Player ID of next player (the teammate)
        """
        # In Guandan, teams are (0,2) and (1,3)
        # Teammate is current player + 2 (mod 4)
        teammate = (self.last_played_player + 2) % 4
        
        # Reset the round - new round starts
        self.public['trace'] = self.trace.copy()
        
        return teammate
    
    def _get_next_player(self, current_player_id):
        """Get next player ID in clockwise order"""
        return (current_player_id + 1) % 4
    
    def get_state(self, player_id):
        """
        Get game state for a player
        
        Args:
            player_id: Player ID
            
        Returns:
            dict: Current game state
        """
        state = {
            'current_player': self.current_player,
            'trace': self.trace,
            'deck': self.public['deck'],
            'played_cards': self.public.get('played_cards', ['' for _ in range(4)]),
            'self': player_id,
            'actions': []  # To be filled by judger
        }
        
        return state
    
    def is_new_round(self):
        """Check if new round started (after wind-taking or game start)"""
        return self.greater_player is None or self.consecutive_passes == 0
    
    def get_wind_taking_status(self):
        """Get wind-taking status for debugging"""
        return {
            'consecutive_passes': self.consecutive_passes,
            'last_played_player': self.last_played_player,
            'current_player': self.current_player
        }
