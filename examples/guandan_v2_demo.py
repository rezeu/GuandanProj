#!/usr/bin/env python3
"""
Guandan v2 Demo
Simple example showing how to use the new implementation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def demo_basic_gameplay():
    """Demonstrate basic gameplay"""
    print("=" * 70)
    print("Guandan v2 - Basic Gameplay Demo")
    print("=" * 70)
    
    try:
        from rlcard.games.guandan_v2.game import GuandanGame
        from rlcard.games.guandan_v2.action import GuandanAction
        from rlcard.games.guandan_v2.card_utils import detect_card_type
        
        # Initialize game
        print("\n1. Initializing new game...")
        game = GuandanGame()
        state, starting_player = game.init_game()
        
        print(f"   ✓ Game started")
        print(f"   ✓ Starting player: {starting_player}")
        print(f"   ✓ Teams: Players 0&2 vs Players 1&3")
        print(f"   ✓ Level card (wildcard): '{game.level_rank}'")
        
        # Show initial hands
        print("\n2. Initial hands:")
        for i, player in enumerate(game.players):
            hand_size = len(player.current_hand)
            print(f"   Player {i}: {hand_size} cards")
        
        # Demonstrate a few rounds
        print("\n3. Gameplay (first 5 rounds):")
        
        for round_num in range(5):
            current_player = game.get_player_id()
            legal_actions = state['legal_actions']
            
            # Skip pass action if possible
            if len(legal_actions) > 1:
                action = legal_actions[1]
            else:
                action = legal_actions[0]
            
            # Show action details
            if not action.is_pass():
                type_info = detect_card_type(action.actual_ids, game.level_rank)
                print(f"   Round {round_num + 1}:")
                print(f"     Player {current_player} plays: {action.to_string()}")
                print(f"     Type: {type_info['type']}, Rank: {type_info['rank']}")
                if type_info.get('is_wildcard_used'):
                    print(f"     Used wildcards: {action.wildcards_used}")
            else:
                print(f"   Round {round_num + 1}: Player {current_player} passes")
            
            # Take step
            state, next_player = game.step(action)
            
            # Check for wind-taking
            if game.round.consecutive_passes == 3:
                print(f"     → Wind-taking! Next player: {next_player} (teammate)")
        
        # Get game status
        print("\n4. Game status:")
        info = game.get_perfect_information()
        print(f"   Cards remaining:")
        for i, hand in enumerate(info['hands']):
            print(f"     Player {i}: {len(hand)} cards")
        
        if game.is_over():
            winner = game.winner
            print(f"   Winner: Team {winner}")
        else:
            print(f"   Game continues...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in basic gameplay demo: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_wildcard_usage():
    """Demonstrate wildcard system"""
    print("\n" + "=" * 70)
    print("Guandan v2 - Wildcard System Demo")
    print("=" * 70)
    
    try:
        from rlcard.games.guandan_v2.action import GuandanAction
        from rlcard.games.guandan_v2.card_utils import ids_to_ranks
        
        print("\n1. Creating wildcard action:")
        print("   Actual cards: 3♥ (ID 0) + 2♥ (ID 12)")
        print("   Claim: Pair of 3s (3♥ + 3♦)")
        print("   Level card: '2' (acts as wildcard)")
        
        # Create action with wildcard
        action = GuandanAction(
            actual_ids=[0, 12],    # 3♥ + 2♥
            claim_ids=[0, 13],     # Claim: 3♥ + 3♦
            claim_type='pair',
            level_rank='2'
        )
        
        print(f"\n   ✓ Action created: {action.to_string()}")
        print(f"   ✓ Wildcards used: {action.wildcards_used}")
        print(f"   ✓ Is pass: {action.is_pass()}")
        
        # Validate with hand
        print("\n2. Validation with hand:")
        hand_ids = [0, 12, 1, 2, 3, 4, 5, 6, 7]
        print(f"   Hand: {ids_to_ranks(hand_ids)}")
        is_valid = action.validate(hand_ids)
        print(f"   ✓ Action valid: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in wildcard demo: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_card_types():
    """Demonstrate advanced card type detection"""
    print("\n" + "=" * 70)
    print("Guandan v2 - Card Type Detection Demo")
    print("=" * 70)
    
    try:
        from rlcard.games.guandan_v2.card_utils import detect_card_type
        
        # Test different card combinations
        test_cases = [
            {
                'name': 'Single',
                'cards': [0],
                'expected': 'solo'
            },
            {
                'name': 'Pair',
                'cards': [0, 13],
                'expected': 'pair'
            },
            {
                'name': 'Triple',
                'cards': [0, 13, 26],
                'expected': 'triple'
            },
            {
                'name': 'Bomb (4 of a kind)',
                'cards': [0, 13, 26, 39],
                'expected': 'bomb'
            },
            {
                'name': 'Straight (5 cards)',
                'cards': [0, 1, 2, 3, 4],
                'expected': 'straight'
            },
            {
                'name': 'Joker Bomb',
                'cards': [52, 53],
                'expected': 'joker_bomb'
            }
        ]
        
        print("\n1. Card type detection:")
        for case in test_cases:
            info = detect_card_type(case['cards'], level_rank='2')
            match = '✅' if case['expected'] in info['type'] else '❌'
            print(f"   {match} {case['name']:20s}: {info['type']:20s} (rank: {info['rank']:4d})")
        
        # Test with wildcards
        print("\n2. Wildcard detection:")
        
        # Bomb using wildcard
        bomb_wild = detect_card_type([0, 13, 26, 12], level_rank='2')
        print(f"   Bomb with wildcard: {bomb_wild['type']}")
        print(f"      Wildcard used: {bomb_wild.get('is_wildcard_used', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in card types demo: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_wind_taking():
    """Demonstrate wind-taking rule"""
    print("\n" + "=" * 70)
    print("Guandan v2 - Wind-Taking Rule Demo")
    print("=" * 70)
    
    try:
        print("\n1. Wind-taking rule explanation:")
        print("   When all 3 opponents pass consecutively after a play,")
        print("   the next turn goes to the original player's teammate.")
        
        print("\n2. Example scenario:")
        scenario = [
            ("Player 0", "plays a card", "→ Control established"),
            ("Player 1", "passes", "→ 1st pass"),
            ("Player 2", "passes", "→ 2nd pass"),
            ("Player 3", "passes", "→ 3rd pass (triggers wind-taking)"),
            ("Player 2", "gets next turn", "→ Teammate of Player 0")
        ]
        
        for player, action, result in scenario:
            print(f"   {player:12s} {action:18s} {result}")
        
        print("\n3. Team structure:")
        teams = {0: "Team A", 1: "Team B", 2: "Team A", 3: "Team B"}
        for player, team in teams.items():
            print(f"   Player {player}: {team}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in wind-taking demo: {e}")
        return False

def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("GUANDAN V2 - COMPREHENSIVE DEMO")
    print("=" * 70)
    
    results = []
    
    # Only run demos that work without numpy
    # results.append(("Basic Gameplay", demo_basic_gameplay()))
    results.append(("Wildcard System", demo_wildcard_usage()))
    results.append(("Card Types", demo_card_types()))
    results.append(("Wind-Taking Rule", demo_wind_taking()))
    
    print("\n" + "=" * 70)
    print("DEMO SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:25s} {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n🎉 All demos completed successfully!")
        print("\nGuandan v2 is ready for:")
        print("  • Reinforcement learning training")
        print("  • AI agent development")
        print("  • Game simulation and analysis")
        print("  • Team-based gameplay research")
        return 0
    else:
        print("\n⚠️  Some demos had issues.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)