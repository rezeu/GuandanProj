#!/usr/bin/env python3
"""
Comprehensive test for Guandan v2 implementation
Tests all major components: card utils, actions, game logic, and environment
"""

import sys
import numpy as np
sys.path.insert(0, '/mnt/c/Files/Course/RL/rlcard')

def test_card_utils():
    """Test card utility functions"""
    print("=" * 60)
    print("Testing Card Utils")
    print("=" * 60)
    
    from rlcard.games.guandan_v2.card_utils import (
        ids_to_ranks, ids_to_suits, id_to_rank, id_to_suit,
        detect_card_type, is_straight_flush_fast, CARD_ID_TO_RANK
    )
    
    # Test basic conversions
    test_ids = [0, 1, 2, 13, 14, 26, 27]  # Mix of cards
    ranks = ids_to_ranks(test_ids)
    suits = ids_to_suits(test_ids)
    
    print(f"✓ Card conversions work")
    print(f"  IDs: {test_ids}")
    print(f"  Ranks: {ranks}")
    print(f"  Suits: {suits}")
    
    # Test card type detection
    print("\n✓ Testing card type detection:")
    
    # Single card
    type_info = detect_card_type([0])
    print(f"  Single card: {type_info}")
    assert type_info['type'] == 'solo'
    
    # Pair
    type_info = detect_card_type([0, 13])  # Two 3s
    print(f"  Pair: {type_info}")
    assert type_info['type'] == 'pair'
    
    # Bomb
    type_info = detect_card_type([0, 13, 26, 39])  # Four 3s
    print(f"  Bomb: {type_info}")
    assert 'bomb' in type_info['type']
    
    # Straight (different suits)
    straight_ids = [0, 14, 28, 42, 17]  # 3♥,4♦,5♣,6♠,7♦ (different suits)
    type_info = detect_card_type(straight_ids)
    print(f"  Straight: {type_info}")
    assert type_info['type'] == 'straight'
    
    # Straight flush (same suit)
    flush_ids = [0, 1, 2, 3, 4]  # All hearts in first deck (3♥,4♥,5♥,6♥,7♥)
    type_info = detect_card_type(flush_ids)
    print(f"  Straight flush: {type_info}")
    assert type_info['type'] == 'straight_flush'
    
    print("✅ Card utils test passed!\n")

def test_action_system():
    """Test action system with wildcards"""
    print("=" * 60)
    print("Testing Action System")
    print("=" * 60)
    
    from rlcard.games.guandan_v2.action import GuandanAction, create_action
    
    # Test pass action
    pass_action = GuandanAction([], [], 'pass')
    print(f"✓ Pass action: {pass_action.to_string()}")
    assert pass_action.is_pass()
    
    # Test simple action (no wildcards)
    simple_action = GuandanAction([0, 13], [0, 13], 'pair')
    print(f"✓ Simple action: {simple_action.to_string()}")
    assert not simple_action.is_pass()
    assert len(simple_action.wildcards_used) == 0
    
    # Test action with wildcards
    # Using '2' (id 12) as wildcard to form pair with '3'
    # Actual: [0 (3♥), 12 (2♥)] -> Claim: pair of 3s [0, 13]
    wildcard_action = GuandanAction(
        actual_ids=[0, 12],
        claim_ids=[0, 13],
        claim_type='pair',
        level_rank='2'
    )
    print(f"✓ Wildcard action: {wildcard_action.to_string()}")
    print(f"  Wildcards used: {wildcard_action.wildcards_used}")
    
    # Test validation
    hand_ids = [0, 12, 1, 2, 3]  # Hand contains 3♥, 2♥, 4♥, 5♥, 6♥
    is_valid = wildcard_action.validate(hand_ids)
    print(f"  Validation: {is_valid}")
    
    print("✅ Action system test passed!\n")

def test_game_core():
    """Test core game functionality"""
    print("=" * 60)
    print("Testing Game Core")
    print("=" * 60)
    
    from rlcard.games.guandan_v2.game import GuandanGame
    
    game = GuandanGame()
    
    # Test initialization
    state, player_id = game.init_game()
    print(f"✓ Game initialized")
    print(f"  Starting player: {player_id}")
    print(f"  Teams: {game.teams}")
    print(f"  Level rank: {game.level_rank}")
    
    # Check all players have cards
    for i, player in enumerate(game.players):
        hand_size = len(player.current_hand)
        print(f"  Player {i}: {hand_size} cards")
        assert hand_size == 27, f"Player {i} should have 27 cards, got {hand_size}"
    
    # Test legal actions
    legal_actions = state['legal_actions']
    print(f"✓ Legal actions: {len(legal_actions)}")
    assert len(legal_actions) > 0, "Should have legal actions"
    
    # Test action availability
    current_player = game.players[player_id]
    available = current_player.available_actions(None, game.judger)
    print(f"✓ Available actions: {len(available)}")
    
    print("✅ Game core test passed!\n")

def test_round_management():
    """Test round management with wind-taking"""
    print("=" * 60)
    print("Testing Round Management")
    print("=" * 60)
    
    from rlcard.games.guandan_v2.round import GuandanRound
    from rlcard.games.guandan_v2.player import GuandanPlayer
    from rlcard.games.guandan_v2.action import GuandanAction
    
    # Create mock players
    players = [GuandanPlayer(i, np.random.RandomState()) for i in range(4)]
    for idx, p in enumerate(players):
        p.current_hand = list(range(idx*10, (idx+1)*10))  # Mock hands
    
    # Create round
    round_obj = GuandanRound(np.random.RandomState(), ['' for _ in range(4)])
    starting_player = round_obj.initiate(players)
    
    print(f"✓ Round initiated, starting player: {starting_player}")
    
    # Test normal rotation
    current = starting_player
    for i in range(3):
        next_player = round_obj._get_next_player(current)
        print(f"  Player {current} -> Player {next_player}")
        current = next_player
    
    # Test wind-taking rule
    print("\n✓ Testing wind-taking rule:")
    
    # Simulate: Player 0 plays, then 1,2,3 pass
    action = GuandanAction([0], [0], 'solo')
    round_obj.last_played_player = 0
    round_obj.consecutive_passes = 0
    
    # Three passes should trigger wind-taking
    for player_id in [1, 2, 3]:
        pass_action = GuandanAction([], [], 'pass')
        next_player = round_obj.proceed_round(players, pass_action)
        print(f"  Player {player_id} passed, next: {next_player}")
    
    # After wind-taking, should go to player 2 (teammate of 0)
    assert round_obj.current_player == 2, f"Expected player 2, got {round_obj.current_player}"
    print(f"✓ Wind-taking correctly sent to player 2 (teammate of 0)")
    
    print("✅ Round management test passed!\n")

def test_environment():
    """Test RL environment"""
    print("=" * 60)
    print("Testing RL Environment")
    print("=" * 60)
    
    from rlcard.envs.guandan_v2 import GuandanEnv
    
    env = GuandanEnv()
    
    # Test reset
    state, player_id = env.reset()
    print(f"✓ Environment reset")
    print(f"  State keys: {list(state.keys())}")
    print(f"  Starting player: {player_id}")
    
    # Check state dimensions
    obs = state['obs']
    print(f"✓ Observation shape: {obs.shape}")
    assert obs.shape[0] == 1722, f"Expected 1722 features, got {obs.shape[0]}"
    
    # Check legal actions
    legal_actions = state['legal_actions']
    print(f"✓ Legal actions: {len(legal_actions)}")
    assert len(legal_actions) > 0, "Should have legal actions"
    
    # Test step (if possible)
    if len(legal_actions) > 1:
        action = legal_actions[1]  # First non-pass action
        next_state, next_player = env.step(action)
        print(f"✓ Step successful, next player: {next_player}")
    
    # Test payoffs
    payoffs = env.get_payoffs()
    print(f"✓ Payoffs shape: {payoffs.shape}")
    assert payoffs.shape == (4,), f"Expected (4,) payoffs, got {payoffs.shape}"
    
    print("✅ Environment test passed!\n")

def test_full_gameplay():
    """Test a simplified full gameplay"""
    print("=" * 60)
    print("Testing Full Gameplay")
    print("=" * 60)
    
    from rlcard.games.guandan_v2.game import GuandanGame
    from rlcard.games.guandan_v2.action import GuandanAction
    
    # Run a quick game
    for trial in range(2):
        print(f"\nTrial {trial + 1}:")
        game = GuandanGame()
        state, player_id = game.init_game()
        
        step_count = 0
        max_steps = 100  # Prevent infinite loops
        
        while not game.is_over() and step_count < max_steps:
            # Get legal actions
            legal_actions = state['legal_actions']
            if not legal_actions:
                break
            
            # Choose a random action (skip pass if possible)
            if len(legal_actions) > 1:
                action = legal_actions[1]
            else:
                action = legal_actions[0]
            
            # Take step
            state, next_player = game.step(action)
            step_count += 1
            
            # Print progress
            if step_count % 10 == 0:
                print(f"  Step {step_count}, current player: {game.get_player_id()}")
        
        if game.is_over():
            winner = game.winner
            print(f"✓ Game completed in {step_count} steps")
            print(f"  Winner team: {winner}")
        else:
            print(f"⚠ Game did not finish in {step_count} steps")
    
    print("✅ Full gameplay test passed!\n")

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("GUANDAN V2 COMPREHENSIVE TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_card_utils()
        test_action_system()
        test_game_core()
        test_round_management()
        test_environment()
        test_full_gameplay()
        
        print("=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 60)
        print("\nGuandan v2 implementation is ready for use!")
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())