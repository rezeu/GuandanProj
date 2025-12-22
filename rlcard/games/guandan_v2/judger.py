"""
Judger for Guandan v2 - Complete implementation with all card types and wildcard support
"""

import itertools
from collections import Counter, defaultdict
from typing import List, Dict, Set, Optional, Tuple

from rlcard.games.guandan_v2.card_utils import (
    detect_card_type, contains_cards, ids_to_ranks, ids_to_suits, ids_to_values,
    RANK_TO_VALUE, RANK_ORDER, id_to_rank, id_to_suit, id_to_value
)
from rlcard.games.guandan_v2.action import GuandanAction

class CardCombination:
    """Represents a card combination with actual and claimed cards"""
    
    def __init__(self, actual_ids: List[int], claim_ids: List[int], claim_type: str, 
                 wildcards_used: Optional[Dict[int, str]] = None):
        self.actual_ids = actual_ids      # Cards actually played from hand
        self.claim_ids = claim_ids        # Cards representing the claimed pattern
        self.claim_type = claim_type      # Type of the claimed pattern
        self.wildcards_used = wildcards_used or {}  # Wildcard usage mapping
    
    def to_action(self, level_rank: str) -> GuandanAction:
        """Convert to GuandanAction"""
        # 创建基础action，wildcards会在GuandanAction内部自动识别
        return GuandanAction(
            actual_ids=self.actual_ids,
            claim_ids=self.claim_ids,
            claim_type=self.claim_type,
            level_rank=level_rank
        )

class GuandanJudger:
    """Complete judger for Guandan game with comprehensive card type support"""
    
    def __init__(self, level_rank: str = '2'):
        """
        Initialize judger
        
        Args:
            level_rank: Current level rank that acts as wildcard (default: '2')
        """
        self.level_rank = level_rank
    
    def set_level_rank(self, level_rank: str):
        """Update level rank (used when players level up)"""
        self.level_rank = level_rank
    
    def get_legal_actions(self, player, greater_player=None):
        """
        Get all legal actions for a player
        
        Args:
            player: GuandanPlayer object
            greater_player: Player who played current highest cards, or None
            
        Returns:
            list: Legal GuandanAction objects
        """
        hand_ids = player.current_hand
        
        if greater_player is None or greater_player.player_id == player.player_id:
            # No cards to beat - can play anything
            return self._get_all_playable_actions(hand_ids)
        else:
            # Need to beat greater player's cards
            greater_action = greater_player.last_action
            return self._get_beat_actions(hand_ids, greater_action)
    
    def _get_all_playable_actions(self, hand_ids):
        """Get all playable actions from hand (no restriction)"""
        actions = [GuandanAction([], [], 'pass', self.level_rank)]
        
        # Get all possible card combinations
        combinations = self._generate_card_combinations(hand_ids)
        
        for combo in combinations:
            action = combo.to_action(self.level_rank)
            actions.append(action)
        
        return actions
    
    def _get_beat_actions(self, hand_ids, greater_action):
        """Get actions that can beat greater_action"""
        actions = [GuandanAction([], [], 'pass', self.level_rank)]
        
        if greater_action is None or greater_action.is_pass():
            return self._get_all_playable_actions(hand_ids)
        
        # Get all possible combinations
        combinations = self._generate_card_combinations(hand_ids)
        
        for combo in combinations:
            if self._can_beat(combo.actual_ids, greater_action):
                action = combo.to_action(self.level_rank)
                actions.append(action)
        
        return actions
    
    def _generate_card_combinations(self, hand_ids):
        """
        Generate all valid card combinations from hand
        
        Args:
            hand_ids: List of card IDs in hand
            
        Returns:
            List of CardCombination objects
        """
        all_combinations = []
        
        # 阶段1: 基础牌型（不考虑癞子）
        basic_combos = self._generate_basic_combinations(hand_ids)
        
        # 阶段2: 复合牌型（组合基础牌型）
        composite_combos = self._generate_composite_combinations(hand_ids, self.level_rank)
        
        # 阶段3: 特殊牌型
        special_combos = self._generate_special_combinations(hand_ids)
        
        # 合并所有原始组合
        all_raw = basic_combos + composite_combos + special_combos
        
        # 阶段4: 癞子优化（增强所有组合）
        for combo in all_raw:
            # 原组合（不使用癞子）
            all_combinations.append(combo)
            
            # 用癞子增强的版本
            enhanced = self._enhance_single_combination(combo, hand_ids, self.level_rank)
            all_combinations.extend(enhanced)
        
        # 去重（基于实际出牌和声称牌型）
        unique_combinations = self._deduplicate_combinations(all_combinations)
        
        return unique_combinations
    
    def _generate_basic_combinations(self, hand_ids):
        """生成所有基础牌型组合（不考虑癞子）"""
        combinations = []
        
        # 1. 单张、对子、三张、炸弹
        rank_groups = self._group_by_rank(hand_ids)
        
        for rank, cards in rank_groups.items():
            # 单张
            for card in cards:
                combinations.append(CardCombination([card], [card], 'solo'))
            
            # 对子
            if len(cards) >= 2:
                for combo in itertools.combinations(cards, 2):
                    actual = list(combo)
                    combinations.append(CardCombination(actual, actual, 'pair'))
            
            # 三张
            if len(cards) >= 3:
                for combo in itertools.combinations(cards, 3):
                    actual = list(combo)
                    combinations.append(CardCombination(actual, actual, 'triple'))
            
            # 炸弹（4-8张）
            if len(cards) >= 4:
                for bomb_size in range(4, min(len(cards), 8) + 1):
                    for combo in itertools.combinations(cards, bomb_size):
                        actual = list(combo)
                        bomb_type = f'bomb_{bomb_size}'
                        combinations.append(CardCombination(actual, actual, bomb_type))
        
        # 2. 顺子（5-12张连续）
        straights = self._find_all_straights(hand_ids)
        combinations.extend(straights)
        
        # 3. 连对（3对以上连续）
        tubes = self._find_all_tubes(hand_ids)
        combinations.extend(tubes)
        
        # 4. 连三（2个以上三连）
        plates = self._find_all_plates(hand_ids)
        combinations.extend(plates)
        
        # 5. 同花顺（5张以上同花连续）
        straight_flushes = self._find_all_straight_flushes(hand_ids)
        combinations.extend(straight_flushes)
        
        return combinations
    
    def _group_by_rank(self, hand_ids):
        """按牌等级分组"""
        groups = {}
        for card_id in hand_ids:
            rank = id_to_rank(card_id)
            if rank not in groups:
                groups[rank] = []
            groups[rank].append(card_id)
        return groups
    
    def _group_by_suit(self, hand_ids):
        """按花色分组"""
        groups = {}
        for card_id in hand_ids:
            suit = id_to_suit(card_id)
            if suit not in groups:
                groups[suit] = []
            groups[suit].append(card_id)
        return groups
    
    def _find_all_straights(self, hand_ids):
        """找所有可能的顺子"""
        straights = []
        values = sorted(set([id_to_value(cid) for cid in hand_ids]))
        
        if len(values) < 5:
            return straights
        
        # 找所有长度5-12的连续序列
        for length in range(5, min(len(values) + 1, 13)):
            for start in range(0, len(values) - length + 1):
                sequence = values[start:start + length]
                if self._is_consecutive(sequence):
                    # 为每个值选择一张牌（避免重复）
                    straight_cards = []
                    used_cards = set()
                    
                    for val in sequence:
                        # 找到该值对应的所有可用牌
                        available = [cid for cid in hand_ids if id_to_value(cid) == val and cid not in used_cards]
                        if available:
                            # 选择第一张未使用的牌
                            selected = available[0]
                            straight_cards.append(selected)
                            used_cards.add(selected)
                    
                    if len(straight_cards) == length:
                        straights.append(CardCombination(straight_cards, straight_cards, 'straight'))
        
        return straights
    
    def _find_all_tubes(self, hand_ids):
        """找所有连对（管子）"""
        tubes = []
        rank_groups = self._group_by_rank(hand_ids)
        
        # 只考虑有对子的rank
        pair_ranks = {rank: cards for rank, cards in rank_groups.items() if len(cards) >= 2}
        
        if len(pair_ranks) < 3:
            return tubes
        
        # 按rank值排序
        sorted_ranks = sorted(pair_ranks.keys(), key=lambda r: RANK_TO_VALUE[r])
        
        # 找连续的对子（3对以上）
        for length in range(3, len(sorted_ranks) + 1):
            for start in range(0, len(sorted_ranks) - length + 1):
                rank_sequence = sorted_ranks[start:start + length]
                
                # 检查是否连续
                is_consecutive = all(
                    RANK_TO_VALUE[rank_sequence[i+1]] - RANK_TO_VALUE[rank_sequence[i]] == 1
                    for i in range(len(rank_sequence) - 1)
                )
                
                if is_consecutive:
                    # 构建连对
                    tube_cards = []
                    for rank in rank_sequence:
                        # 取前2张牌
                        tube_cards.extend(rank_groups[rank][:2])
                    
                    tubes.append(CardCombination(tube_cards, tube_cards, 'tube'))
        
        return tubes
    
    def _find_all_plates(self, hand_ids):
        """找所有连三（钢板）"""
        plates = []
        rank_groups = self._group_by_rank(hand_ids)
        
        # 只考虑有三张的rank
        triple_ranks = {rank: cards for rank, cards in rank_groups.items() if len(cards) >= 3}
        
        if len(triple_ranks) < 2:
            return plates
        
        # 按rank值排序
        sorted_ranks = sorted(triple_ranks.keys(), key=lambda r: RANK_TO_VALUE[r])
        
        # 找连续的三连（2个以上）
        for length in range(2, len(sorted_ranks) + 1):
            for start in range(0, len(sorted_ranks) - length + 1):
                rank_sequence = sorted_ranks[start:start + length]
                
                # 检查是否连续
                is_consecutive = all(
                    RANK_TO_VALUE[rank_sequence[i+1]] - RANK_TO_VALUE[rank_sequence[i]] == 1
                    for i in range(len(rank_sequence) - 1)
                )
                
                if is_consecutive:
                    # 构建连三
                    plate_cards = []
                    for rank in rank_sequence:
                        # 取前3张牌
                        plate_cards.extend(rank_groups[rank][:3])
                    
                    plates.append(CardCombination(plate_cards, plate_cards, 'plate'))
        
        return plates
    
    def _find_all_straight_flushes(self, hand_ids):
        """找所有同花顺"""
        straight_flushes = []
        
        # 按花色分组
        suit_groups = self._group_by_suit(hand_ids)
        
        # 对每个花色找顺子
        for suit, cards in suit_groups.items():
            if len(cards) < 5:
                continue
                
            # 在该花色中找顺子
            values = sorted(set([id_to_value(cid) for cid in cards]))
            
            for length in range(5, min(len(values) + 1, 13)):
                for start in range(0, len(values) - length + 1):
                    sequence = values[start:start + length]
                    if self._is_consecutive(sequence):
                        # 构建同花顺
                        flush_straight = []
                        for val in sequence:
                            available = [cid for cid in cards if id_to_value(cid) == val]
                            if available:
                                flush_straight.append(available[0])
                        
                        if len(flush_straight) == length:
                            straight_flushes.append(CardCombination(
                                flush_straight, flush_straight, 'straight_flush'
                            ))
        
        return straight_flushes
    
    def _generate_composite_combinations(self, hand_ids, level_rank):
        """生成复合牌型（三带一、三带二、钢板等）"""
        composites = []
        
        # 1. 三带一（triple + solo）
        triples = self._find_all_triples(hand_ids)
        solos = self._find_all_solos(hand_ids)
        
        for triple in triples:
            for solo in solos:
                # 检查是否有牌重复（更严格的检查）
                if not set(triple.actual_ids) & set(solo.actual_ids):
                    actual = triple.actual_ids + solo.actual_ids
                    claim = triple.claim_ids + [triple.claim_ids[0]]  # 声称三带一
                    composites.append(CardCombination(actual, claim, 'triple_solo'))
        
        # 2. 三带二/俘虏（triple + pair）
        pairs = self._find_all_pairs(hand_ids)
        
        for triple in triples:
            for pair in pairs:
                if not set(triple.actual_ids) & set(pair.actual_ids):  # 无交集
                    actual = triple.actual_ids + pair.actual_ids
                    claim = triple.claim_ids + [triple.claim_ids[0], triple.claim_ids[0]]
                    composites.append(CardCombination(actual, claim, 'full_house'))
        
        # 3. 钢板（两个三连）
        plates = self._find_all_plates(hand_ids)
        composites.extend(plates)
        
        return composites
    
    def _generate_special_combinations(self, hand_ids):
        """生成特殊牌型（王炸）"""
        specials = []
        
        # 王炸（BJ + RJ）
        bj_cards = [cid for cid in hand_ids if id_to_rank(cid) == 'BJ']
        rj_cards = [cid for cid in hand_ids if id_to_rank(cid) == 'RJ']
        
        if bj_cards and rj_cards:
            actual = [bj_cards[0], rj_cards[0]]
            claim = [bj_cards[0], rj_cards[0]]
            specials.append(CardCombination(actual, claim, 'joker_bomb'))
        
        return specials
    
    def _enhance_single_combination(self, combo, hand_ids, level_rank):
        """用癞子增强单个组合"""
        enhanced = []
        wildcards = [cid for cid in hand_ids if id_to_rank(cid) == level_rank]
        
        if not wildcards:
            return enhanced
        
        # 用癞子替换部分牌（升级牌型）
        if combo.claim_type in ['solo', 'pair', 'triple']:
            for num_wildcards in range(1, min(len(wildcards), 3) + 1):
                # 确保不重复添加已经在combo中的癞子
                new_wildcards = [w for w in wildcards[:num_wildcards] if w not in combo.actual_ids]
                if not new_wildcards:
                    continue
                
                # 用癞子替换，保持声称牌型
                actual_with_wild = combo.actual_ids + new_wildcards
                new_combo = CardCombination(
                    actual_ids=actual_with_wild,
                    claim_ids=combo.claim_ids,  # 声称牌型不变
                    claim_type=combo.claim_type,
                    wildcards_used={w: combo.claim_ids[0] for w in new_wildcards}
                )
                enhanced.append(new_combo)
        
        return enhanced
    
    def _deduplicate_combinations(self, combinations):
        """去重：基于actual_ids和claim_ids"""
        seen = set()
        unique = []
        
        for combo in combinations:
            key = (tuple(sorted(combo.actual_ids)), 
                   tuple(sorted(combo.claim_ids)), 
                   combo.claim_type)
            if key not in seen:
                seen.add(key)
                unique.append(combo)
        
        return unique
    
    def _find_all_solos(self, hand_ids):
        """找所有单张"""
        return [CardCombination([card], [card], 'solo') for card in hand_ids]
    
    def _find_all_pairs(self, hand_ids):
        """找所有对子"""
        pairs = []
        rank_groups = self._group_by_rank(hand_ids)
        
        for rank, cards in rank_groups.items():
            if len(cards) >= 2:
                for combo in itertools.combinations(cards, 2):
                    actual = list(combo)
                    pairs.append(CardCombination(actual, actual, 'pair'))
        
        return pairs
    
    def _find_all_triples(self, hand_ids):
        """找所有三张"""
        triples = []
        rank_groups = self._group_by_rank(hand_ids)
        
        for rank, cards in rank_groups.items():
            if len(cards) >= 3:
                for combo in itertools.combinations(cards, 3):
                    actual = list(combo)
                    triples.append(CardCombination(actual, actual, 'triple'))
        
        return triples
    
    def _is_consecutive(self, values):
        """Check if values are consecutive"""
        return all(values[i+1] - values[i] == 1 for i in range(len(values)-1))
    
    def _can_beat(self, combo_ids, greater_action):
        """Check if combo can beat greater_action"""
        combo_type = detect_card_type(combo_ids, self.level_rank)
        greater_type = detect_card_type(greater_action.claim_ids, self.level_rank)
        
        if combo_type['type'] == 'invalid':
            return False
        
        # Special types (bombs, straight flushes) can beat anything lower
        if combo_type['rank'] >= 800 or greater_type['rank'] >= 800:
            return combo_type['rank'] > greater_type['rank']
        
        # Same type with same length
        if (combo_type['type'] == greater_type['type'] and 
            len(combo_ids) == len(greater_action.claim_ids)):
            return combo_type['main_value'] > greater_type['main_value']
        
        return False
    
    def validate_play(self, action, player, greater_player):
        """
        Validate if a play is legal
        
        Args:
            action: GuandanAction to validate
            player: Player making the play
            greater_player: Player to beat, or None
            
        Returns:
            bool: True if play is valid
        """
        if action.is_pass():
            return True
        
        # Check action is in player's hand
        if not contains_cards(player.current_hand, action.actual_ids, self.level_rank):
            return False
        
        # Check action type is valid
        type_info = detect_card_type(action.actual_ids, self.level_rank)
        if type_info['type'] == 'invalid':
            return False
        
        # Check if we need to beat someone
        if greater_player and greater_player.last_action:
            return self._can_beat(action.actual_ids, greater_player.last_action)
        
        return True

def id_to_rank(card_id):
    """Get rank from card ID"""
    from rlcard.games.guandan_v2.card_utils import id_to_rank as get_rank
    return get_rank(card_id)

def id_to_value(card_id):
    """Get comparison value from card ID"""
    from rlcard.games.guandan_v2.card_utils import id_to_value as get_value
    return get_value(card_id)