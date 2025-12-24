"""
Game class for Guandan v2
Main game logic integrating all components
"""

import numpy as np
from rlcard.games.guandan_v2.round import GuandanRound
from rlcard.games.guandan_v2.judger import GuandanJudger
from rlcard.games.guandan_v2.player import GuandanPlayer

def init_deck():
    """Import deck initialization from utils"""
    from rlcard.utils import init_108_deck
    return init_108_deck()

class GuandanGame:
    """
    Guandan Game class
    
    4-player team-based card game with:
    - Wildcard system (level cards)
    - Straight flush detection
    - Wind-taking rule (接风)
    """
    
    def __init__(self, allow_step_back=False):
        """
        Initialize Guandan game
        
        Args:
            allow_step_back: Whether to allow undo actions (for RL)
        """
        self.np_random = np.random.RandomState()
        self.allow_step_back = allow_step_back
        self.num_players = 4
        self.players = None
        self.round = None
        self.judger = None
        self.state = None
        self.winner = None
        self.history = []
        
        # Game settings
        self.level_rank = '2'  # Current level card that acts as wildcard
        self.max_bomb_size = 8
        
        # Team setup: players 0&2 vs players 1&3
        self.teams = {0: 0, 1: 1, 2: 0, 3: 1}  # player_id -> team_id
    
    def init_game(self):
        """Initialize a new game"""
        # Initialize players
        self.players = [GuandanPlayer(i, self.np_random) for i in range(self.num_players)]
        
        # Initialize round
        self.round = GuandanRound(self.np_random, ['' for _ in range(self.num_players)])
        starting_player = self.round.initiate(self.players)
        
        # Initialize judger
        self.judger = GuandanJudger(self.level_rank)
        
        # Initialize game state
        self.state = {
            'current_player': starting_player,
            'trace': [],
            'deck': self.round.public['deck'],
            'played_cards': ['' for _ in range(self.num_players)],
            'legal_actions': [],
            'winner': None,
            'level_rank': self.level_rank
        }
        
        # Get initial legal actions
        legal_actions = self.round.players[starting_player].available_actions(
            None, self.judger
        )
        self.state['legal_actions'] = legal_actions
        
        self.winner = None
        self.history = []
        
        return self.state, starting_player
    
    def get_num_players(self):
        """Get number of players in the game"""
        return self.num_players
    
    def step(self, action):
        """
        Take one step in the game
        
        Args:
            action: GuandanAction to take
            
        Returns:
            tuple: (next_state, next_player_id)
        """
        if self.allow_step_back:
            # Save current state for undo
            self.history.append({
                'players': [p.current_hand.copy() for p in self.players],
                'round': self.round.get_state(0),
                'state': self.state.copy(),
                'winner': self.winner,
                'level_rank': self.level_rank
            })
        
        current_player = self.state['current_player']
        player = self.players[current_player]
        
        # Record action
        self.state['trace'].append((current_player, action))
        
        # Process action
        greater_player = self.round.greater_player
        next_player_id = self.round.proceed_round(self.players, action)
        
        # Update state
        self.state['current_player'] = next_player_id
        self.state['played_cards'] = self.round.public['played_cards']
        
        # Check if game is over
        if self._is_game_over():
            self.winner = self._get_winner()
            self.state['winner'] = self.winner
        else:
            # Get legal actions for next player
            next_player = self.players[next_player_id]
            legal_actions = next_player.available_actions(
                self.round.greater_player, self.judger
            )
            self.state['legal_actions'] = legal_actions
        
        return self.state, next_player_id
    
    def _is_game_over(self):
        # Count how many players in each team have finished
        team_finish_count = {team_id: 0 for team_id in self.teams.values()}

        for player in self.players:
            if len(player.current_hand) == 0:
                team_id = self.teams[player.player_id]
                team_finish_count[team_id] += 1

        # Game over when any team has both players finished
        return any(count == 2 for count in team_finish_count.values())

    
    def _get_winner(self):
        team_finish_count = {team_id: 0 for team_id in self.teams.values()}

        for player in self.players:
            if len(player.current_hand) == 0:
                team_id = self.teams[player.player_id]
                team_finish_count[team_id] += 1

        for team_id, count in team_finish_count.items():
            if count == 2:
                return team_id

        return None
    
    def get_player_num(self):
        """Get number of players"""
        return self.num_players
    
    def get_action_num(self):
        """Get number of possible actions"""
        # Dynamic based on action space
        return 400  # Approximate max
    
    def get_player_id(self):
        """Get current player ID"""
        return self.state['current_player']
    
    def is_over(self):
        """Check if game is over"""
        return self.winner is not None
    
    def step_back(self):
        """Step back to previous state (if allowed)"""
        if not self.allow_step_back or not self.history:
            return False
        
        # Restore previous state
        prev_state = self.history.pop()
        
        for i, player in enumerate(self.players):
            player.current_hand = prev_state['players'][i]
        
        self.round = GuandanRound(self.np_random, ['' for _ in range(self.num_players)])
        # Note: Full round restore would need more implementation
        
        self.state = prev_state['state']
        self.winner = prev_state['winner']
        self.level_rank = prev_state['level_rank']
        
        return True
    
    def get_perfect_information(self):
        """Get perfect information for debugging/analysis"""
        info = {
            'hands': [p.current_hand for p in self.players],
            'trace': self.state['trace'],
            'winner': self.winner,
            'teams': self.teams,
            'level_rank': self.level_rank,
            'wind_taking_status': self.round.get_wind_taking_status()
        }
        
        return info
    
    def set_level_rank(self, level_rank):
        """Update level rank (for leveling system)"""
        self.level_rank = level_rank
        if self.judger:
            self.judger.set_level_rank(level_rank)
        self.state['level_rank'] = level_rank

# Test function
def test_game_basic():
    """Test basic game functionality"""
    game = GuandanGame()
    
    print("Testing Guandan v2 game...")
    
    # Initialize game
    state, player_id = game.init_game()
    print(f"✓ Game initialized, starting player: {player_id}")
    print(f"✓ Players: {game.num_players}")
    print(f"✓ Teams: {game.teams}")
    
    # Check hands
    for i, player in enumerate(game.players):
        print(f"  Player {i}: {len(player.current_hand)} cards")
        assert len(player.current_hand) == 27, f"Player {i} should have 27 cards"
    
    print("✓ All players have correct number of cards")
    
    # Test actions
    legal_actions = state['legal_actions']
    print(f"✓ Legal actions: {len(legal_actions)} available")
    
    # Take a step
    if legal_actions:
        action = legal_actions[1]  # Skip pass action
        next_state, next_player = game.step(action)
        print(f"✓ Step taken, next player: {next_player}")
    
    print("✅ Basic game test passed!")

if __name__ == "__main__":
    test_game_basic()