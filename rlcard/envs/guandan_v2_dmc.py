"""
Environment for Guandan v2 with DMC training support
Optimized for direct GuandanAction passing (no action_id)
"""

from collections import Counter, OrderedDict
import numpy as np

from rlcard.envs import Env
from rlcard.games.guandan_v2.game import GuandanGame
from rlcard.games.guandan_v2.action import GuandanAction
from rlcard.games.guandan_v2.card_utils import ids_to_ranks, cards_to_ids, contains_cards, RANK_TO_VALUE, RANK_ORDER

class GuandanEnvForDMC(Env):
    """
    Guandan Environment optimized for DMC training
    
    State shape: [4, 1722] (4 players, 1722 features)
    Action shape: [4, 143] (4 players, 108 cards + 35 action features)
    
    Key difference: This version directly passes GuandanAction objects
    instead of using action_id mapping, avoiding ID collision issues.
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
        self.action_shape = [[143] for _ in range(self.game.num_players)]  # 143-dim compact encoding
        
        # Store last legal actions for training
        self.last_legal_actions = []
    
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
        extracted_state['legal_actions'] = self._get_legal_actions()  # Return GuandanAction objects
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
            'legal_actions': legal_actions,  # Now returns GuandanAction objects
            'raw_obs': state,
            'raw_legal_actions': [a for a in state['actions']],
            'action_record': state['trace']
        }
        
        return extracted_state
    
    def _get_legal_actions(self):
        """
        Get all legal actions - now returns GuandanAction objects directly
        
        Returns:
            list: Legal GuandanAction objects
        """
        legal_actions = self.game.state['legal_actions']
        action_objects = []
        
        for action in legal_actions:
            if isinstance(action, str) and action == 'pass':
                # Pass action
                action_objects.append(GuandanAction([], [], 'pass', self.game.level_rank))
            elif isinstance(action, GuandanAction):
                # Already a GuandanAction
                action_objects.append(action)
            else:
                # Handle other types (should not happen)
                action_objects.append(GuandanAction([], [], 'pass', self.game.level_rank))
        
        self.last_legal_actions = action_objects  # Store for encoding reference
        return action_objects
    
    def step(self, action):
        """
        Step forward with GuandanAction (no decoding needed!)
        
        Args:
            action: GuandanAction object
            
        Returns:
            (tuple): (next_state, next_player_id)
        """
        # Validate action - ensure the player has the cards
        current_player_id = self.get_player_id()
        current_player = self.game.players[current_player_id]
        
        if not action.is_pass() and not contains_cards(current_player.current_hand, action.actual_ids, self.game.level_rank):
            print(f"[ERROR] Attempting to play invalid action!")
            print(f"  Player: {current_player_id}")
            print(f"  Hand: {sorted(current_player.current_hand)}")
            print(f"  Action actual_ids: {sorted(action.actual_ids)}")
            # Default to pass
            action = GuandanAction([], [], 'pass', self.game.level_rank)
        
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
    
    def get_action_feature(self, action):
        """
        Get action feature for DMC agent using compact 143-dim encoding.
        Encoding: 108 (cards) + 1 (pass) + 10 (type) + 14 (rank) + 8 (length) + 2 (wildcards) = 143
        
        Args:
            action: GuandanAction object (directly passed, no ID mapping needed!)
            
        Returns:
            numpy.array: Action feature vector (143,)
        """
        feature = np.zeros(143, dtype=np.float32)  # 143维特征
        
        # Validate action type
        if not isinstance(action, GuandanAction):
            print(f"[WARNING] Invalid action type: {type(action)}, defaulting to pass")
            action = GuandanAction([], [], 'pass', self.game.level_rank)
        
        # 1. 过牌处理
        if action.is_pass() or not action.actual_ids or len(action.actual_ids) == 0:
            feature[108] = 1  # 过牌标识（第108维）
            feature[118] = 1  # 牌型类型中的pass类型（第118维）
            return feature
        
        # 1. 实际出牌编码 (0-107维) - Multi-hot编码
        for card_id in action.actual_ids:
            if 0 <= card_id < 108:
                feature[card_id] = 1.0
        
        # 2. 过牌标识 (108维) - 已经是0
        
        # 3. 牌型类型编码 (109-118维)
        type_mapping = {
            'solo': 109,
            'pair': 110, 
            'triple': 111,
            'triple_solo': 112,
            'full_house': 113,
            'straight': 114,
            'bomb_4': 115, 'bomb_5': 115, 'bomb_6': 115,
            'bomb_7': 115, 'bomb_8': 115,  # 所有炸弹都用115维
            'straight_flush': 116,
            'joker_bomb': 117,
            'pass': 118
        }
        action_type = action.claim_type
        if action_type in type_mapping:
            feature[type_mapping[action_type]] = 1.0
        
        # 4. 主牌等级编码 (119-132维，共14维)
        main_rank = self._get_main_rank(action)
        if main_rank in RANK_TO_VALUE:
            rank_value = RANK_TO_VALUE[main_rank]
            # 将15个等级映射到14维，合并BJ/RJ为一个维度
            if main_rank in ['BJ', 'RJ']:
                rank_index = 132  # 最后一个维度用于大小王
            else:
                rank_index = min(119 + rank_value, 131)  # 限制在119-131范围
            if 119 <= rank_index < 133:
                feature[rank_index] = 1.0
        
        # 5. 出牌长度编码 (133-140维，共8维)
        num_cards = len(action.actual_ids)
        if num_cards >= 8:
            feature[140] = 1.0
        elif 1 <= num_cards <= 7:
            feature[132 + num_cards] = 1.0  # 133维对应1张牌
        
        # 6. 癞子使用情况编码 (141-142维，共2维)
        wildcard_count = len(action.wildcards_used) if hasattr(action, 'wildcards_used') else 0
        feature[141] = min(8, wildcard_count) / 8.0  # 使用癞子数量，归一化到0-1
        feature[142] = 1.0 if wildcard_count > 0 else 0.0  # 是否使用癞子
        
        return feature
    
    def _get_main_rank(self, action):
        """
        Get the main rank of the action for encoding
        Args:
            action: GuandanAction object
        Returns:
            str: Main rank of the action
        """
        if action.claim_type in ['solo', 'pair', 'triple', 'full_house', 'triple_solo']:
            # For these types, main rank is the rank of the main cards
            ranks = ids_to_ranks(action.claim_ids)
            if ranks:
                if action.claim_type == 'full_house':
                    from collections import Counter
                    rank_counts = Counter(ranks)
                    for rank, count in rank_counts.items():
                        if count >= 3:
                            return rank
                    return ranks[0]
                else:
                    return ranks[0]
        elif action.claim_type in ['straight', 'straight_flush']:
            # For straights, max card determines the rank
            values = ids_to_ranks(action.claim_ids)
            if values:
                return max(values, key=lambda r: RANK_TO_VALUE.get(r, 0))
        elif action.claim_type and action.claim_type.startswith('bomb'):
            ranks = ids_to_ranks(action.claim_ids)
            if ranks:
                return ranks[0]
        
        return '3'  # Default to lowest rank
    
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

# Test function
def test_environment():
    """Test environment functionality"""
    print("Testing Guandan v2 DMC environment...")
    
    env = GuandanEnvForDMC()
    
    # Reset
    state, player_id = env.reset()
    print(f"✓ Reset successful, starting player: {player_id}")
    
    # Check state
    assert 'obs' in state, "State should contain 'obs'"
    assert 'legal_actions' in state, "State should contain 'legal_actions'"
    print(f"✓ State format correct")
    print(f"  - Obs shape: {state['obs'].shape}")
    print(f"  - Legal actions: {len(state['legal_actions'])}")
    
    # Check legal actions are GuandanAction objects
    if len(state['legal_actions']) > 0:
        assert isinstance(state['legal_actions'][0], GuandanAction), "Legal actions should be GuandanAction objects"
        print(f"✓ Legal actions are GuandanAction objects")
    
    # Test action encoding
    from rlcard.games.guandan_v2.action import GuandanAction
    
    # Test 1: Pass action
    pass_action = GuandanAction([], [], 'pass', '2')
    pass_feature = env.get_action_feature(pass_action)
    print(f"✓ Pass action feature shape: {pass_feature.shape}")
    assert pass_feature.shape == (143,), f"Expected shape (143,), got {pass_feature.shape}"
    assert pass_feature[108] == 1.0, 'Pass flag should be 1'
    assert pass_feature[118] == 1.0, 'Pass type should be 1'
    print("  - Pass encoding correct")
    
    # Test 2: Pair action
    pair_action = GuandanAction([7, 34], [7, 34], 'pair', '2')  # Two 8s
    pair_feature = env.get_action_feature(pair_action)
    print(f"✓ Pair action feature shape: {pair_feature.shape}")
    assert pair_feature.shape == (143,), f"Expected shape (143,), got {pair_feature.shape}"
    assert pair_feature[7] == 1.0, 'Card 7 should be marked'
    assert pair_feature[34] == 1.0, 'Card 34 should be marked'
    assert pair_feature[110] == 1.0, 'Pair type should be marked'
    print("  - Pair encoding correct")
    
    # Take a random legal action
    legal_actions = state['legal_actions']
    if len(legal_actions) > 1:
        action = legal_actions[1]  # Skip pass
        next_state, next_player = env.step(action)
        print(f"✓ Step successful, next player: {next_player}")
    
    # Get payoffs
    payoffs = env.get_payoffs()
    print(f"✓ Payoffs shape: {payoffs.shape}")
    
    print("✅ Environment test passed!")
    print("\n🎉 Direct GuandanAction passing design verified!")

if __name__ == "__main__":
    test_environment()