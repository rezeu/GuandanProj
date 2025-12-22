"""
测试重复牌ID的bug
"""
import sys
sys.path.append('.')
from rlcard.games.guandan_v2.judger import GuandanJudger
from rlcard.games.guandan_v2.card_utils import cards_to_ids

def test_duplicate_bug():
    """测试重复牌ID的问题"""
    judger = GuandanJudger(level_rank='2')
    
    # 一个可能导致重复的手牌
    hand = cards_to_ids("5678999TTTJJJQQQKKKAAA22")
    print(f"手牌大小: {len(hand)}")
    print(f"手牌: {sorted(hand)}")
    
    # 生成所有组合
    combinations = judger._generate_card_combinations(hand)
    
    print(f"\n生成组合数: {len(combinations)}")
    
    # 查找有重复的组合
    duplicates_found = []
    for i, combo in enumerate(combinations):
        if len(combo.actual_ids) != len(set(combo.actual_ids)):
            duplicates_found.append((i, combo))
    
    print(f"\n发现重复的组合数: {len(duplicates_found)}")
    
    for idx, combo in duplicates_found[:5]:  # 显示前5个
        print(f"\n组合索引: {idx}")
        print(f"  claim_type: {combo.claim_type}")
        print(f"  actual_ids: {combo.actual_ids}")
        print(f"  claim_ids: {combo.claim_ids}")
        # 统计重复
        from collections import Counter
        counts = Counter(combo.actual_ids)
        duplicates = {card: count for card, count in counts.items() if count > 1}
        print(f"  重复项: {duplicates}")
        
        # 打印使用癞子的情况
        if combo.wildcards_used:
            print(f"  wildcards_used: {combo.wildcards_used}")
    
    # 特定测试：检查复合牌型
    print("\n" + "="*60)
    print("测试复合牌型生成...")
    
    # 找一个有三张和对子的手牌
    test_hand = cards_to_ids("33344")  # 三个3 + 两个4
    triples = judger._find_all_triples(test_hand)
    pairs = judger._find_all_pairs(test_hand)
    
    print(f"手牌: {test_hand}")
    print(f"找到的三张: {len(triples)}")
    for t in triples:
        print(f"  {t.actual_ids}")
    print(f"找到的对子: {len(pairs)}")
    for p in pairs:
        print(f"  {p.actual_ids}")

if __name__ == "__main__":
    test_duplicate_bug()