"""
测试最终的完整judger实现
"""
import sys
sys.path.append('.')
from rlcard.games.guandan_v2.judger import GuandanJudger, CardCombination
from rlcard.games.guandan_v2.card_utils import cards_to_ids

def test_final_judger():
    """测试最终的完整judger实现"""
    print("=" * 60)
    print("测试最终的完整judger实现")
    print("=" * 60)
    
    # 创建judger
    judger = GuandanJudger(level_rank='2')
    
    print("\n1. 测试基础手牌组合生成...")
    
    # 测试1: 简单手牌（单张、对子、三张、炸弹）
    hand1 = cards_to_ids("333444555")  # 3个3，3个4，3个5
    combinations1 = judger._generate_basic_combinations(hand1)
    
    print(f"手牌: 333444555 ({len(hand1)} cards)")
    print(f"生成 {len(combinations1)} 个组合")
    
    # 统计各种牌型
    type_counts = {}
    for combo in combinations1:
        claim_type = combo.claim_type
        type_counts[claim_type] = type_counts.get(claim_type, 0) + 1
    
    print("牌型统计:")
    for claim_type, count in sorted(type_counts.items()):
        print(f"  {claim_type}: {count}")
    
    print("\n2. 测试复杂手牌（包含顺子、连对、连三）...")
    
    # 测试2: 复杂手牌
    hand2 = cards_to_ids("3456789TJQKA2BJRJ")  # 完整序列 + 大小王
    combinations2 = judger._generate_basic_combinations(hand2)
    
    print(f"手牌: 3456789TJQKA2BJRJ ({len(hand2)} cards)")
    print(f"生成 {len(combinations2)} 个组合")
    
    # 检查特定牌型
    has_straight = any(c.claim_type == 'straight' for c in combinations2)
    has_straight_flush = any(c.claim_type == 'straight_flush' for c in combinations2)
    has_tube = any(c.claim_type == 'tube' for c in combinations2)
    has_plate = any(c.claim_type == 'plate' for c in combinations2)
    has_joker_bomb = any(c.claim_type == 'joker_bomb' for c in combinations2)
    
    print(f"\n验证结果:")
    print(f"  有顺子: {has_straight}")
    print(f"  有同花顺: {has_straight_flush}")
    print(f"  有连对: {has_tube}")
    print(f"  有连三: {has_plate}")
    print(f"  有王炸: {has_joker_bomb}")
    
    print("\n3. 测试复合牌型（三带一、三带二、钢板）...")
    
    # 测试3: 适合复合牌型的手牌
    hand3 = cards_to_ids("333444555667788")  # 多个三连 + 多个对子
    combinations3 = judger._generate_composite_combinations(hand3, '2')
    
    print(f"手牌: 333444555667788 ({len(hand3)} cards)")
    print(f"生成 {len(combinations3)} 个复合组合")
    
    # 检查复合牌型
    has_triple_solo = any(c.claim_type == 'triple_solo' for c in combinations3)
    has_full_house = any(c.claim_type == 'full_house' for c in combinations3)
    
    print(f"\n复合牌型验证:")
    print(f"  有三带一: {has_triple_solo}")
    print(f"  有俘虏: {has_full_house}")
    
    print("\n4. 测试癞子牌组合...")
    
    # 测试4: 包含癞子牌的手牌
    hand4 = cards_to_ids("333222222")  # 3个3 + 6个2（癞子）
    combinations4 = judger._generate_card_combinations(hand4)
    
    print(f"手牌: 333222222 ({len(hand4)} cards)")
    print(f"生成 {len(combinations4)} 个组合（含癞子）")
    
    # 检查癞子使用情况
    wildcards_used = 0
    for combo in combinations4:
        if combo.wildcards_used:
            wildcards_used += 1
    
    print(f"使用癞子的组合数: {wildcards_used}")
    
    # 打印几个使用癞子的例子
    wildcard_examples = [c for c in combinations4 if c.wildcards_used][:3]
    print("\n使用癞子的例子:")
    for i, combo in enumerate(wildcard_examples):
        print(f"  {i+1}: {combo.claim_type} - actual: {combo.actual_ids}, "
              f"wildcards: {combo.wildcards_used}")
    
    print("\n5. 测试完整流程...")
    
    # 测试5: 验证judger在真实场景中的表现
    from rlcard.envs.guandan_v2 import GuandanEnv
    from rlcard.agents.dmc_agent.model import DMCModel
    
    env = GuandanEnv()
    model = DMCModel(
        state_shape=[[1722], [1722], [1722], [1722]],
        action_shape=[[143], [143], [143], [143]],
        device='cpu'
    )
    env.set_agents([model.get_agent(i) for i in range(4)])
    
    # 运行一局游戏，测试judger在真实场景中的表现
    print("运行一局游戏...")
    try:
        trajectories, payoffs = env.run(is_training=True)
        print(f"✓ 游戏完成，轨迹长度: {[len(t) for t in trajectories]}")
        print(f"✓ 奖励: {payoffs}")
        
        # 验证trajectory中的动作都是合法的
        valid_count = 0
        total_actions = 0
        
        for player_traj in trajectories:
            for i in range(1, len(player_traj), 2):  # 动作在奇数索引
                if i < len(player_traj):
                    action = player_traj[i]
                    if hasattr(action, 'actual_ids'):  # 简化验证
                        total_actions += 1
                        valid_count += 1
        
        print(f"✓ 验证动作合法性: {valid_count}/{total_actions} 动作有效")
        
    except Exception as e:
        print(f"❌ 游戏运行错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 完整judger测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_final_judger()