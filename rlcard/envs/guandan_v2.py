"""
Environment for Guandan v2
Wrapper for RL training
"""

from collections import Counter, OrderedDict
import numpy as np

from rlcard.envs import Env
from rlcard.games.guandan_v2.game import GuandanGame
from rlcard.games.guandan_v2.action import GuandanAction
from rlcard.games.guandan_v2.card_utils import ids_to_ranks, cards_to_ids

class GuandanEnv(Env):
    """
    Guandan Environment for RL training
    
    State shape: [4, 1722] (4 players, 1722 features)
    Action shape: [4, 400] (4 players, max 400 actions)
    """
    
    def __init__(self, config=None):
        """
        Initialize Guandan environment
        
        Args:
            config: Configuration dict
        """
        self.name = 'guandan_v2'
        self.game = GuandanGame()
        self.default_game_config = {
            'level_rank': '2',
            'allow_step_back': False,
            'seed': None
        }
        
        config = config or {}
        for key, value in self.default_game_config.items():
            config[key] = config.get(key, value)
        
        super().__init__(config)
        
        # State and action shapes
        self.state_shape = [[1722] for _ in range(self.game.num_players)]
        self.action_shape = [[400] for _ in range(self.game.num_players)]
        
        # Runtime action ID mapping (for combination games)
        self.action_id_map = {}  # Map action_id -> GuandanAction
    
    def reset(self):
        """
        Reset environment and return initial observation
        
        Returns:
            state (dict): Initial state with 'obs', 'legal_actions', etc.
            player_id (int): Starting player ID
        """
        # Initialize game
        game_state, player_id = self.game.init_game()
        
        # Get player's full state from the player's perspective
        player = self.game.players[player_id]
        public = self.game.round.public
        
        # Construct full observation state
        legal_actions = game_state['legal_actions']
        
        # Create player state
        player_state = player.get_state(
            public=public,
            others_hand=[],  # Will be calculated
            num_cards_left=[p.hand_size for p in self.game.players],
            actions=legal_actions
        )
        
        # Extract RL observation
        extracted_state = self._extract_state(player_state)
        extracted_state['legal_actions'] = self._get_legal_actions()
        extracted_state['raw_obs'] = player_state
        extracted_state['raw_legal_actions'] = legal_actions
        extracted_state['action_record'] = self.game.state['trace']
        
        self.timestep = 0
        
        return extracted_state, player_id
        
    def _extract_state(self, state):
        """
        Extract state representation
        
        Args:
            state: Raw game state
            
        Returns:
            dict: Processed state
        """
        current_hand = self._cards2array(state.get('hand', state.get('current_hand', [])))
        others_hand = self._cards2array(state.get('others_hand', []))
        
        # Process last action
        last_action = ''
        if len(state['trace']) != 0:
            if state['trace'][-1][1] == 'pass':
                last_action = state['trace'][-2][1] if len(state['trace']) >= 2 else ''
            else:
                last_action = state['trace'][-1][1]
        last_action = self._cards2array(last_action)
        
        # Process action sequence
        recent_actions = self._action_seq2array(self._process_action_seq(state['trace']))
        
        # Player positioning
        player_id = state['self']
        teammate = (player_id + 2) % 4
        opponent_up = (player_id + 3) % 4
        opponent_down = (player_id + 1) % 4
        
        # Get played cards for each position
        teammate_played = self._cards2array(state['played_cards'][teammate])
        opponent_up_played = self._cards2array(state['played_cards'][opponent_up])
        opponent_down_played = self._cards2array(state['played_cards'][opponent_down])
        
        # Stack all features
        obs = np.concatenate([
            current_hand,          # 0-107: Current hand
            others_hand,           # 108-215: Others' cards
            teammate_played,       # 216-323: Teammate played
            opponent_up_played,    # 324-431: Upper opponent played
            opponent_down_played,  # 432-539: Lower opponent played
            last_action,           # 540-647: Last action
            recent_actions,        # 648-1655: Recent 9 actions
            # Additional features can be added up to 1722
        ])
        
        # Fill remaining with zeros if needed
        if len(obs) < 1722:
            obs = np.concatenate([obs, np.zeros(1722 - len(obs))])
        
        legal_actions = self._get_legal_actions()
        
        extracted_state = {
            'obs': obs,
            'legal_actions': legal_actions,
            'raw_obs': state,
            'raw_legal_actions': [a for a in state['actions']],
            'action_record': state['trace']
        }
        
        return extracted_state
    
    def _get_legal_actions(self):
        """
        Get all legal actions and store mapping
        
        Returns:
            list: Legal action IDs
        """
        legal_actions = self.game.state['legal_actions']
        action_ids = []
        self.action_id_map = {}  # Reset mapping
        
        for action in legal_actions:
            if isinstance(action, str):
                # Pass action
                action_ids.append(0)  # Reserve 0 for pass
                self.action_id_map[0] = GuandanAction([], [], 'pass', self.game.level_rank)
            elif hasattr(action, 'to_action_id'):
                # GuandanAction - dynamic ID
                action_id = action.to_action_id()
                action_ids.append(action_id)
                self.action_id_map[action_id] = action
            else:
                action_ids.append(0)
        
        return list(set(action_ids))  # Remove duplicates
    
    def _decode_action(self, action_id):
        """
        Decode action ID to GuandanAction using runtime mapping
        
        Args:
            action_id: Action ID
            
        Returns:
            GuandanAction
        """
        if action_id == 0:
            return GuandanAction([], [], 'pass', self.game.level_rank)
        
        # Use runtime mapping if available
        if hasattr(self, 'action_id_map') and action_id in self.action_id_map:
            return self.action_id_map[action_id]
        
        # Fallback: try to decode from action space (for basic actions)
        action_space = self._get_action_space()
        if action_id < len(action_space):
            action_str = action_space[action_id]
            return GuandanAction.from_string(action_str, [], self.game.level_rank)
        
        # Last resort: pass
        return GuandanAction([], [], 'pass', self.game.level_rank)
    
    def _get_action_space(self):
        """Get all possible action strings"""
        # For now, use a predefined action space
        # In production, this should be generated based on all possible card combinations
        actions = ['pass']
        
        # Add all single cards
        actions.extend([rank for rank in ids_to_ranks(range(15))])
        
        # Add pairs (33, 44, 55, ...)
        for rank in ids_to_ranks(range(13)):  # 3-2
            actions.append(rank * 2)
        
        # Add triples
        for rank in ids_to_ranks(range(13)):
            actions.append(rank * 3)
        
        # Add bombs (4-8 of same rank)
        for rank in ids_to_ranks(range(13)):
            for size in range(4, 9):
                actions.append(rank * size)
        
        return actions
    
    def _cards2array(self, cards):
        """Convert cards to array representation"""
        if isinstance(cards, str):
            # Convert string to IDs
            card_ids = cards_to_ids(cards)
        elif isinstance(cards, (list, np.ndarray)):
            card_ids = cards
        else:
            card_ids = []
        
        # Create one-hot encoding
        arr = np.zeros(108)
        if len(card_ids) > 0:
            arr[card_ids] = 1
        
        return arr
    
    def _action_seq2array(self, action_seq):
        """Convert action sequence to array"""
        # Encode last 9 actions (or fewer if not available)
        seq_len = min(9, len(action_seq))
        arr = np.zeros(9 * 108)  # 9 actions * 108 cards
        
        for i in range(seq_len):
            action = action_seq[-(i+1)]
            if isinstance(action, str) and action != 'pass':
                card_ids = cards_to_ids(action)
                start_idx = i * 108
                for cid in card_ids:
                    if cid < 108:  # Ensure within bounds
                        arr[start_idx + cid] = 1
        
        return arr
    
    def _process_action_seq(self, trace):
        """Process action sequence from trace"""
        # Extract just the action strings from trace
        actions = []
        for player_id, action in trace:
            if isinstance(action, GuandanAction):
                if action.is_pass():
                    actions.append('pass')
                else:
                    actions.append(''.join(ids_to_ranks(action.claim_ids)))
            elif isinstance(action, str):
                actions.append(action)
        
        return actions
    
    def step(self, action, raw_action=False):
        """
        Step forward with action decoding and state extraction
        
        Args:
            action (int): Action ID from agent
            raw_action (boolean): True if action is already decoded
            
        Returns:
            (tuple): (next_state, next_player_id)
        """
        if not raw_action:
            action = self._decode_action(action)
        
        self.timestep += 1
        # Record action
        self.action_recorder.append((self.get_player_id(), action))
        
        # Execute in game
        next_state, player_id = self.game.step(action)
        
        # Get player's complete state for the next player
        player = self.game.players[player_id]
        public = self.game.round.public
        legal_actions = self.game.state['legal_actions']
        
        # Build complete observation state
        player_state = player.get_state(
            public=public,
            others_hand=[],  # Calculate if needed
            num_cards_left=[p.hand_size for p in self.game.players],
            actions=legal_actions
        )
        
        # Extract RL observation
        extracted_state = self._extract_state(player_state)
        extracted_state['legal_actions'] = self._get_legal_actions()
        extracted_state['raw_obs'] = player_state
        extracted_state['raw_legal_actions'] = legal_actions
        extracted_state['action_record'] = self.game.state['trace']
        
        return extracted_state, player_id
    
    def get_payoffs(self):
        """
        Get payoffs for each player
        
        Returns:
            numpy array: Payoffs for 4 players
        """
        if not self.game.is_over():
            return np.zeros(4)
        
        winner_team = self.game.winner
        payoffs = np.zeros(4)
        
        # Reward winning team, penalize losing team
        for player_id in range(4):
            if self.game.teams[player_id] == winner_team:
                payoffs[player_id] = 1.0
            else:
                payoffs[player_id] = -1.0
        
        return payoffs
    
    def get_perfect_information(self):
        """Get perfect information for analysis"""
        return self.game.get_perfect_information()
    
    def set_level_rank(self, level_rank):
        """Update level rank for leveling system"""
        self.game.set_level_rank(level_rank)

# Test function
def test_environment():
    """Test environment functionality"""
    print("Testing Guandan v2 environment...")
    
    env = GuandanEnv()
    
    # Reset
    state, player_id = env.reset()
    print(f"✓ Reset successful, starting player: {player_id}")
    
    # Check state
    assert 'obs' in state, "State should contain 'obs'"
    assert 'legal_actions' in state, "State should contain 'legal_actions'"
    print(f"✓ State format correct")
    print(f"  - Obs shape: {state['obs'].shape}")
    print(f"  - Legal actions: {len(state['legal_actions'])}")
    
    # Take random action
    legal_actions = state['legal_actions']
    if len(legal_actions) > 1:
        action = legal_actions[1]  # Skip pass
        next_state, next_player = env.step(action)
        print(f"✓ Step successful, next player: {next_player}")
    
    # Get payoffs
    payoffs = env.get_payoffs()
    print(f"✓ Payoffs shape: {payoffs.shape}")
    
    print("✅ Environment test passed!")

if __name__ == "__main__":
    test_environment()