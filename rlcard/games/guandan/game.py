# -*- coding: utf-8 -*-
''' Implement Guandan Game class
'''
import functools
from heapq import merge
import numpy as np
import numpy as np
import random
import warnings
from collections import Counter, OrderedDict
import json

class Game:
    ''' Provide game APIs for env to run Guandan and get corresponding state
    information.
    '''
    def __init__(self, allow_step_back=False):
        self.allow_step_back = allow_step_back
        self.np_random = np.random.RandomState()
        self.num_players = 4
        self.current_player = 0

        self.cardscale = ['A','2','3','4','5','6','7','8','9','0','J','Q','K']
        self.suitset = ['h','d','s','c']
        self.point_order = ['2', '3', '4', '5', '6', '7', '8', '9', '0', 'J', 'Q', 'K', 'A']
        self.Normaltypes = ("single", "pair", "three", "straight", "set", "three_straight", "triple_pairs")
        self.scaletypes = ("straight", "three_straight", "triple_pairs")
        self.Utils = Utils()
        self.level = None
        self.seed = None
        self.done = False
        self.game_state_info = "Init"
        self.cleared = [] # list of cleared players (have played all their decks)
        self.agent_names = ['player_%d' % i for i in range(4)]
        self.errset = {
            0: "Initialization Fault",
            1: "PlayerAction Fault",
            2: "Game Fault"
        }

    def init_game(self, config={}):
        ''' Initialize players and state.

        Returns:
            dict: first state in one game
            int: current player's id
        '''
        '''
        Call this function to start different matches
        @ config: contains match initalization info

        '''
        self.np_random = np.random.RandomState()
        self.num_players = 4
        self.current_player = 0

        self.cardscale = ['A','2','3','4','5','6','7','8','9','0','J','Q','K']
        self.suitset = ['h','d','s','c']
        self.point_order = ['2', '3', '4', '5', '6', '7', '8', '9', '0', 'J', 'Q', 'K', 'A']
        self.Normaltypes = ("single", "pair", "three", "straight", "set", "three_straight", "triple_pairs")
        self.scaletypes = ("straight", "three_straight", "triple_pairs")
        self.Utils = Utils()
        self.level = None
        self.seed = None
        self.done = False
        self.game_state_info = "Init"
        self.cleared = [] # list of cleared players (have played all their decks)
        self.agent_names = ['player_%d' % i for i in range(4)]
        self.errset = {
            0: "Initialization Fault",
            1: "PlayerAction Fault",
            2: "Game Fault"
        }
        if 'seed' in config:
            self.seed = config['seed']
            random.seed(self.seed)
        if 'level' in config and config['level'] in self.cardscale:
            self.level = config['level']
        else:
            self.level = '2'
            warnings.warn("ResetConfigWarning: Level configuration fault or no level designated.")
            
        self.point_order = ['2', '3', '4', '5', '6', '7', '8', '9', '0', 'J', 'Q', 'K', 'A']
        self._set_level()
        self.total_deck = [i for i in range(108)]
        self.card_todeal = [i for i in range(108)]
        random.shuffle(self.card_todeal)
        self.player_decks = [self.card_todeal[dpos*27 : (dpos+1) * 27] for dpos in range(4)]
        self.done = False
        self.history = []  
        self.round = 0
        self.played_cards = [[] for _ in range(4)]
        self.reward = {
            0: 0,
            1: 0,
            2: 0,
            3: 0
        }
        self.pass_on = -1
        self.lastMove = {
            'player': -1, # the first round
            'response': [[], []]
            }
        self.cleared = []
        self.game_state_info = "Running"

        return self.get_state(self.current_player), self.current_player # Each match starts from the player on 0 position

    def step(self, response):
        ''' Perform one draw of the game

        Args:
            action (str): specific action of Guandan. Eg: '33344'

        Returns:
            dict: next player's state
            int: next player's id
        '''
        self.round += 1
        self.reward = None
        curr_player = response['player']
        action = response['response'][0]
        claim = response['response'][1]
        if not self._is_legal_claim(action, claim): # not a legal claim
            self.game_state_info = f"Player {curr_player}: ILLEGAL CLAIM"
            return self._end_game(curr_player)
        for poker_no in action: 
            if poker_no in self.player_decks[curr_player]:
                self.player_decks[curr_player].remove(poker_no)
                self.played_cards[curr_player].append(poker_no)
            else:
                self.game_state_info = f"Player {curr_player}: NOT YOUR POKER"
                return self._end_game(curr_player)
        cur_pokertype, cur_points = self._check_poker_type(claim)
        if cur_pokertype == 'invalid':
            self.game_state_info = f"Player {curr_player}: INVALID TYPE"
            return self._end_game(curr_player)
        if len(self.lastMove['response'][0]) == 0: # first-hand
            if cur_pokertype == 'pass':
                self.game_state_info = f"Player {curr_player}: ILLEGAL PASS AS FIRST-HAND"
                return self._end_game(curr_player)
            self.lastMove = response
            self.pass_on = -1
        else:
            if cur_pokertype != 'pass': # if currplayer passes, do nothing
                last_pokertype, last_points = self._check_poker_type(self.lastMove['response'][1])
                bigger = self._check_bigger(last_pokertype, last_points, cur_pokertype, cur_points)
                if bigger == "error":
                    self.game_state_info = f"Player {curr_player}: POKERTYPE MISMATCH"
                    return self._end_game(curr_player)
                if not bigger:
                    self.game_state_info = f"Player {curr_player}: CANNOT BEAT LASTMOVE"
                    return self._end_game(curr_player)
                self.lastMove = response
                self.pass_on = -1
        
        self.history.append(response)
        if len(self.player_decks[curr_player]) == 0: # Finishing this round
            self.cleared.append(curr_player)
            if len(self.cleared) == 3: # match sealed
                self.done = True
                self.game_state_info = "Finished"
            elif len(self.cleared) == 2 and (self.cleared[1] - self.cleared[0]) % 2 == 0:
                self.done = True
                self.game_state_info = "Finished"
            self.pass_on = curr_player
            
        self._set_reward()
        if not self.done:
            next_player = (curr_player + 1) % 4
            if next_player == self.pass_on: # Successfully pass to teammate
                next_player = (self.pass_on + 2) % 4
            self.lastMove = {
                'player': -1, 
                'response': [[], []]
                }
            while next_player in self.cleared:
                next_player = (next_player + 1) % 4
                if next_player == self.pass_on: # Successfully pass to teammate
                    next_player = (self.pass_on + 2) % 4
                    self.lastMove = {
                        'player': -1, 
                        'response': [[], []]
                    }

            if next_player == self.lastMove['player']:
                self.lastMove = {
                    'player': -1, 
                    'response': [[], []]
                }
            self.current_player = next_player
            return self.get_state(next_player) , next_player
        return self.get_state(0) , 0
    def get_state(self, player_id):
        ''' Return player's state

        Args:
            player_id (int): player id

        Returns:
            (dict): The state of the player
        '''
        state = OrderedDict({'obs': self._get_obs(player_id), 'legal_actions': self._get_legal_actions(player_id) })
        return state

    @staticmethod
    def get_num_actions():
        ''' Return the total number of abstract acitons

        Returns:
            int: the total number of abstract actions of Guandan
        '''
        
        return 216

    def get_player_id(self):
        ''' Return current player's id

        Returns:
            int: current player's id
        '''
        return self.current_player

    def get_num_players(self):
        ''' Return the number of players in Guandan

        Returns:
            int: the number of players in Guandan
        '''
        return self.num_players

    def is_over(self):
        ''' Judge whether a game is over

        Returns:
            Bool: True(over) / False(not over)
        '''
        return self.done
    
    def _set_reward(self):
        '''
        setting rewards
        if terminating: winner team gets reward 1~3
        else: rewards 0
        '''
        self.reward = {
            0: 0,
            1: 0,
            2: 0,
            3: 0
        }
        if self.done:
            self.current_player = -1
            if len(self.cleared) == 2: # Must be a double-dweller
                self.reward[self.cleared[0]] = 3
                self.reward[self.cleared[1]] = 3
            elif (self.cleared[2] - self.cleared[0]) % 2 == 0:
                self.reward[self.cleared[0]] = 2
                self.reward[self.cleared[2]] = 2
            else:
                self.reward[self.cleared[0]] = 1
                self.reward[(self.cleared[0] + 2) % 4] = 1
    
    def _raise_error(self, errno, detail):
        raise Error(self.errset[errno]+": "+detail)
    
    def _end_game(self, fault_player):
        '''
        ending game on player's action exceptions
        '''
        self.reward = {
            0: 0,
            1: 0,
            2: 0,
            3: 0
        }
        self.done = True
        self.reward[fault_player] = -3
        return self.get_state(-1)
    
    def _get_obs(self, player):
        '''
        getting observation for player
        player: player_id (-1: all players)
        '''
        obs_set = {}
        for i in range(4):
            obs_set[i] = {
                "id": i,
                "level": self.level,
                "status": self.game_state_info,
                "deck": self.player_decks[i],
                "last_move": self.lastMove,
                "history": self.history,
                "reward": self.reward[i]
            }
        if player == -1:
            return obs_set[0]
        else:
            return obs_set[player] 

                
    def _set_level(self):     
        self.point_order.remove(self.level)
        self.point_order.append(self.level)
        self.point_order.extend(["o", "O"])
        
    def _is_legal_claim(self, action: list, claim: list):
        covering = "h" + self.level
        if len(action) != len(claim):
            return False
        action_pok = [self.Utils.Num2Poker(p) for p in action]
        claim_pok = [self.Utils.Num2Poker(p) for p in claim]
        for pok in action_pok:
            if pok != covering:
                if pok in claim_pok:
                    claim_pok.remove(pok)
                else:
                    return False
        for pok in claim_pok:
            if pok[1] == 'o' or pok[1] == 'O':
                return False
        return True
    
    def _check_poker_type(self, poker: list):
        if poker == []:
            return "pass", ()
        # covering = "h" + level
        poker = [self.Utils.Num2Poker(p) for p in poker]
        if len(poker) == 1:
            return "single", (poker[0][1])
        if len(poker) == 2:
            if poker[0][1] == poker[1][1]:
                return "pair", (poker[0][1])
            return "invalid", ()
        # 大于等于三张
        points = [p[1] for p in poker]
        cnt = Counter(points)
        vals = list(cnt.values())
        if len(poker) == 3:
            if "o" in points: 
                return "invalid", ()
            if vals.count(3) == 1:
                return "three", (points[0])
            return "invalid", ()
        if len(poker) == 4: # should be a bomb
            if "o" in points or "O" in points: # should be a rocket
                if cnt["o"] == 2 and cnt["O"] == 2:
                    return "rocket", ("jo")
                return "invalid", ()
            if vals.count(4) == 1:
                return "bomb", (4, points[0])
            return "invalid", ()
        if len(poker) == 5: # could be straight, straight flush, three&two or bomb
            if vals.count(5) == 1:
                return "bomb", (5, points[0])
            if vals.count(3) == 1 and vals.count(2) == 1: # set: 三带二 
                three = ''
                two = ''
                for k in list(cnt.keys()):
                    if cnt[k] == 3:
                        three = k
                    elif cnt[k] == 2:
                        two = k
                return "set", (three, two)
            if vals.count(1) == 5: # should be straight
                points.sort(key=lambda x: self.cardscale.index(x))
                suits = [p[0] for p in poker]
                suit_cnt = Counter(suits)
                suit_vals = list(suit_cnt.values())
                flush = False
                if suit_vals.count(5) == 1:
                    flush = True
                first = points[0]
                if first == 'A':
                    if points == ['A', '0', 'J', 'Q', 'K']:
                        if flush:
                            return "straight_flush", ('0')
                        return "straight", ('0')
                sup_straight = [self.cardscale[self.cardscale.index(first)+i] for i in range(5)]
                if points == sup_straight:
                    if flush:
                        return "straight_flush", (first)
                    return "straight", (first)
            return "invalid", ()
        if len(poker) == 6: # could be triple_pairs, three_straight, bomb
            if vals.count(6) == 1:
                return "bomb", (6, points[0])
            if vals.count(3) == 2:
                ks = []
                for k in list(cnt.keys()):
                    ks.append(k)
                ks.sort(key=lambda x: self.cardscale.index(x))
                if 'A' in ks:
                    if ks == ['A', '2']:
                        return "three_straight", ('A')
                    if ks == ['A', 'K']:
                        return "three_straight", ('K')
                    return "invalid", ()
                if self.cardscale.index(ks[1]) - self.cardscale.index(ks[0]) == 1:
                    return "three_straight", (ks[0])
            if vals.count(2) == 3:
                ks = []
                for k in list(cnt.keys()):
                    ks.append(k)
                ks.sort(key=lambda x: self.cardscale.index(x))
                if 'A' in ks:
                    if ks == ['A', 'Q', 'K']:
                        return "triple_pairs", ('Q')
                    if ks == ['A', '2', '3']:
                        return "triple_pairs", ('A')
                    return "invalid", ()
                pairs = [self.cardscale[self.cardscale.index(ks[0])+i] for i in range(3)]
                if ks == pairs:
                    return "triple_pairs", (ks[0])
            return "invalid", ()
        if len(poker) > 6 and len(poker) <= 10:
            if vals.count(len(poker)) == 1:
                bomb = points[0]
                return "bomb", (len(poker), bomb)
        return "invalid", ()
    
    def _check_bigger(self, type1, point1, type2, point2):
        '''
        Check if poker2(type2, point2) is bigger than poker1(type1, point1)
        Assumption: type1 and type2 are VALID cardtypes. Must check types before calling this function 
        '''
        if type2 == "rocket":
            return True
        if type1 == "rocket":
            return False
        if type1 in self.Normaltypes:
            if type2 not in self.Normaltypes:
                return True
            if type1 == type2:
                if type1 in self.scaletypes and self.cardscale.index(point2[0]) > self.cardscale.index(point1[0]):
                    return True
                if type1 not in self.scaletypes and self.point_order.index(point2[0]) > self.point_order.index(point1[0]):
                    return True
                return False
            return "error"
        if type2 in self.Normaltypes:
            return "error"
        if type1 == "bomb":
            if type2 == "bomb":
                if point2[0] == point1[0] and self.point_order.index(point2[1]) > self.point_order.index(point1[1]):
                    return True
                if point2[0] > point1[0]:
                    return True
            if type2 == "straight_flush":
                if point1[0] < 6:
                    return True
        if type1 == "straight_flush":
            if type2 == "bomb":
                if point2[0] >= 6:
                    return True
                return False
            if type2 == "straight_flush":
                if self.cardscale.index(point2[0]) > self.cardscale.index(point1[0]):
                    return True
        return False
    
    def _get_legal_actions(self, player):
        '''
        获取玩家的合法动作（完整版，考虑级牌）
        '''

        if player == -1 or self.done:
            return []
        
        legal_actions = []
        hand = sorted(self.player_decks[player])
        
        # 生成所有可能的牌型
        all_moves = self._generate_all_moves_with_level(hand)
        
        # 如果是首出，可以选择任何非空动作
        if self.lastMove['player'] == -1 or self.lastMove['player'] == player:
            legal_actions = [move for move in all_moves if move['response'][0]]
        else:
            # 需要压制上家
            last_type, last_points = self._check_poker_type(self.lastMove['response'][1])
            
            for move in all_moves:
                if not move['response'][0]:  # pass
                    legal_actions.append(move)
                else:
                    cur_type, cur_points = self._check_poker_type(move['response'][1])
                    if self._check_bigger(last_type, last_points, cur_type, cur_points) == True:
                        legal_actions.append(move)
        
        # 添加pass选项（如果不是首出）
        if self.lastMove['player'] != -1 and self.lastMove['player'] != player:
            found_pass = False
            for move in legal_actions:
                if not move['response'][0]:
                    found_pass = True
                    break
            if not found_pass:
                legal_actions.append({
                    'player': player,
                    'response': [[],[]]
                })
        return legal_actions

    def _generate_all_moves_with_level(self, hand):
        '''
        生成所有可能的出牌组合（考虑级牌）
        '''
        moves = []
        hand_pokers = [self.Utils.Num2Poker(card) for card in hand]
        
        # 按点数和花色分组
        point_groups = {}
        suit_groups = {}
        
        for i, card in enumerate(hand):
            poker = hand_pokers[i]
            point = poker[1] if len(poker) > 1 else poker
            suit = poker[0] if len(poker) > 1 else ''
            
            if point not in point_groups:
                point_groups[point] = []
            point_groups[point].append(card)
            
            if suit:
                if suit not in suit_groups:
                    suit_groups[suit] = {}
                if point not in suit_groups[suit]:
                    suit_groups[suit][point] = []
                suit_groups[suit][point].append(card)
        
        # 1. 单张
        for card in hand:
            moves.append({
                'player': self.current_player,
                'response': [[card], [card] ]
            })
        
        # 2. 对子（包括级牌对子）
        moves.extend(self._generate_pairs_with_level(point_groups))
        
        # 3. 三连对（考虑级牌顺序）
        moves.extend(self._generate_triple_pairs_with_level(point_groups))
        
        # 4. 三同张
        moves.extend(self._generate_threes_with_level(point_groups))
        
        # 5. 三同连张（考虑级牌顺序）
        moves.extend(self._generate_three_straights_with_level(point_groups))
        
        # 6. 三带二
        moves.extend(self._generate_three_with_two_with_level(point_groups))
        
        # 7. 顺子（考虑级牌限制）
        moves.extend(self._generate_straights_with_level(point_groups))
        
        # 8. 炸弹（包括级牌炸弹）
        moves.extend(self._generate_bombs_with_level(point_groups))
        
        # 9. 同花顺（考虑级牌限制）
        moves.extend(self._generate_straight_flushes_with_level(suit_groups))
        
        # 10. 火箭（大小王各两张）
        moves.extend(self._generate_rockets_with_level(point_groups))
        
        # 去重
        return self._remove_duplicate_moves(moves)
    
    def _remove_duplicate_moves(self, moves):
        '''
        去除重复的动作
        '''
        # 简单去重：基于动作列表去重
        unique_moves = []
        seen_actions = set()
        
        for move in moves:
            action_key = tuple(sorted(move['response'][0]))
            if action_key not in seen_actions:
                seen_actions.add(action_key)
                unique_moves.append(move)
        
        return unique_moves

    def _get_point_order_with_level(self):
        '''获取考虑级牌的点数顺序'''
        # 基础顺序（不包括王）
        base_order = ['2', '3', '4', '5', '6', '7', '8', '9', '0', 'J', 'Q', 'K', 'A']
        
        # 移除级牌
        if self.level in base_order:
            base_order.remove(self.level)
        
        # 添加级牌到正确位置
        if self.level == '2':
            # 当级牌是2时，A最大，2次之
            base_order.insert(0, '2')  # 2在3前面
        elif self.level == 'A':
            # 当级牌是A时，A最大
            base_order.append('A')
        else:
            # 其他级牌：找到级牌应该插入的位置
            level_index = self.cardscale.index(self.level)
            base_order.insert(level_index, self.level)
        
        return base_order

    def _get_consecutive_points(self, start_point, length):
        '''获取从start_point开始连续length个点数（考虑级牌顺序）'''
        point_order = self._get_point_order_with_level()
        
        try:
            start_idx = point_order.index(start_point)
            if start_idx + length > len(point_order):
                return None
            
            return point_order[start_idx:start_idx+length]
        except ValueError:
            return None

    def _is_consecutive_with_level(self, points):
        '''检查点数是否连续（考虑级牌顺序）'''
        if len(points) < 2:
            return True
        
        point_order = self._get_point_order_with_level()
        
        for i in range(len(points)-1):
            try:
                idx1 = point_order.index(points[i])
                idx2 = point_order.index(points[i+1])
                if idx2 - idx1 != 1:
                    return False
            except ValueError:
                return False
        
        return True

    def _generate_pairs_with_level(self, point_groups):
        '''生成对子（包括级牌对子）'''
        moves = []
        
        for point, cards in point_groups.items():
            if len(cards) >= 2:
                from itertools import combinations
                for combo in combinations(cards, 2):
                    moves.append({
                        'player': self.current_player,
                        'response': [list(combo),list(combo)]
                    })
        
        return moves

    def _generate_triple_pairs_with_level(self, point_groups):
        '''生成三连对（考虑级牌顺序）'''
        moves = []
        
        # 获取考虑级牌的点数顺序
        point_order = self._get_point_order_with_level()
        
        # 检查每个点数是否至少有2张牌
        available_points = []
        for point in point_order:
            if point in point_groups and len(point_groups[point]) >= 2:
                available_points.append(point)
        
        # 寻找三个连续的点数
        for i in range(len(available_points) - 2):
            p1, p2, p3 = available_points[i], available_points[i+1], available_points[i+2]
            
            # 检查是否连续
            if self._is_consecutive_with_level([p1, p2, p3]):
                # 检查级牌限制：当2是级牌时，不可以作KK AA 22打出
                if self.level == '2' and p1 == 'K' and p2 == 'A' and p3 == '2':
                    continue
                
                # 生成所有组合
                from itertools import product, combinations
                p1_pairs = list(combinations(point_groups[p1], 2))
                p2_pairs = list(combinations(point_groups[p2], 2))
                p3_pairs = list(combinations(point_groups[p3], 2))
                
                for pair1 in p1_pairs:
                    for pair2 in p2_pairs:
                        for pair3 in p3_pairs:
                            combo = list(pair1) + list(pair2) + list(pair3)
                            moves.append({
                                'player': self.current_player,
                                'response': [combo,combo]
                            })
        
        return moves

    def _generate_threes_with_level(self, point_groups):
        '''生成三同张'''
        moves = []
        
        for point, cards in point_groups.items():
            if len(cards) >= 3:
                from itertools import combinations
                for combo in combinations(cards, 3):
                    moves.append({
                        'player': self.current_player,
                        'response': [list(combo),list(combo)]
                    })
        
        return moves

    def _generate_three_straights_with_level(self, point_groups):
        '''生成三同连张（考虑级牌顺序）'''
        moves = []
        
        # 获取考虑级牌的点数顺序
        point_order = self._get_point_order_with_level()
        
        # 检查每个点数是否至少有3张牌
        available_points = []
        for point in point_order:
            if point in point_groups and len(point_groups[point]) >= 3:
                available_points.append(point)
        
        # 寻找两个连续的点数
        for i in range(len(available_points) - 1):
            p1, p2 = available_points[i], available_points[i+1]
            
            # 检查是否连续
            if self._is_consecutive_with_level([p1, p2]):
                # 生成所有组合
                from itertools import product, combinations
                p1_threes = list(combinations(point_groups[p1], 3))
                p2_threes = list(combinations(point_groups[p2], 3))
                
                for three1 in p1_threes:
                    for three2 in p2_threes:
                        combo = list(three1) + list(three2)
                        moves.append({
                            'player': self.current_player,
                            'response': [combo, combo]
                        })
        
        return moves

    def _generate_three_with_two_with_level(self, point_groups):
        '''生成三带二'''
        moves = []
        
        # 收集所有三张和所有对子
        threes = []
        pairs = []
        
        for point, cards in point_groups.items():
            if len(cards) >= 3:
                from itertools import combinations
                threes.extend([(point, list(combo)) for combo in combinations(cards, 3)])
            
            if len(cards) >= 2:
                from itertools import combinations
                pairs.extend([(point, list(combo)) for combo in combinations(cards, 2)])
        
        # 组合三张和对子
        for three_point, three_combo in threes:
            for pair_point, pair_combo in pairs:
                if three_point != pair_point:
                    combo = three_combo + pair_combo
                    moves.append({
                        'player': self.current_player,
                        'response': [combo, combo]
                    })
        
        return moves

    def _generate_straights_with_level(self, point_groups):
        '''生成顺子（考虑级牌限制）'''
        moves = []
        
        # 获取考虑级牌的点数顺序
        point_order = self._get_point_order_with_level()
        
        # 检查每个点数是否至少有1张牌
        available_points = []
        for point in point_order:
            if point in point_groups and len(point_groups[point]) >= 1:
                available_points.append(point)
        
        # 寻找五个连续的点数
        for i in range(len(available_points) - 4):
            points_subset = available_points[i:i+5]
            
            # 检查是否连续
            if self._is_consecutive_with_level(points_subset):
                # 检查顺子是否合法：不能组成J、Q、K、A、2（2是级牌时）
                if self.level == '2' and points_subset == ['J', 'Q', 'K', 'A', '2']:
                    continue
                
                # 生成所有组合
                from itertools import product
                card_options = []
                for point in points_subset:
                    card_options.append(point_groups[point])
                
                for combo in product(*card_options):
                    moves.append({
                        'player': self.current_player,
                        'response': [list(combo),list(combo)]
                    })
        
        return moves

    def _generate_bombs_with_level(self, point_groups):
        '''生成炸弹（包括级牌炸弹）'''
        moves = []
        
        for point, cards in point_groups.items():
            if len(cards) >= 4:
                from itertools import combinations
                n = len(cards)
                for k in range(4, min(n, 8) + 1):
                    for combo in combinations(cards, k):
                        moves.append({
                            'player': self.current_player,
                            'response': [list(combo), list(combo)]
                        })
        
        return moves

    def _generate_straight_flushes_with_level(self, suit_groups):
        '''生成同花顺（考虑级牌限制）'''
        moves = []
        
        # 获取考虑级牌的点数顺序
        point_order = self._get_point_order_with_level()
        
        for suit, point_cards in suit_groups.items():
            # 检查每个点数是否至少有1张该花色的牌
            available_points = []
            for point in point_order:
                if point in point_cards and len(point_cards[point]) >= 1:
                    available_points.append(point)
            
            # 寻找五个连续的点数
            for i in range(len(available_points) - 4):
                points_subset = available_points[i:i+5]
                
                # 检查是否连续
                if self._is_consecutive_with_level(points_subset):
                    # 检查顺子是否合法：不能组成J、Q、K、A、2（2是级牌时）
                    if self.level == '2' and points_subset == ['J', 'Q', 'K', 'A', '2']:
                        continue
                    
                    # 每个点数取一张该花色的牌
                    combo = []
                    for point in points_subset:
                        combo.append(point_cards[point][0])
                    
                    moves.append({
                        'player': self.current_player,
                        'response': [combo, combo]
                    })
        
        return moves

    def _generate_rockets_with_level(self, point_groups):
        '''生成火箭（大小王各两张）'''
        moves = []
        
        # 检查是否有大小王
        if 'o' in point_groups and 'O' in point_groups:
            jo_cards = point_groups['o']
            jO_cards = point_groups['O']
            
            # 需要大小王各至少两张
            if len(jo_cards) >= 2 and len(jO_cards) >= 2:
                from itertools import combinations, product
                jo_pairs = list(combinations(jo_cards, 2))
                jO_pairs = list(combinations(jO_cards, 2))
                
                for jo_pair in jo_pairs:
                    for jO_pair in jO_pairs:
                        combo = list(jo_pair) + list(jO_pair)
                        moves.append({
                            'player': self.current_player,
                            'response': [combo,combo]
                        })
        
        return moves
    
import numpy as np
import random


class Utils():
    
    def __init__(self):
        self.cardscale = ['A','2','3','4','5','6','7','8','9','0','J','Q','K']
        self.suitset = ['h','d','s','c']
        self.jokers = ['jo', 'jO']
    
    def Num2Poker(self, num: int):
        num_in_deck = num % 54
        if num_in_deck == 52:
            return "jo"
        if num_in_deck == 53:
            return "jO"
        # Normal cards:
        pokernumber = self.cardscale[num_in_deck // 4]
        pokersuit = self.suitset[num_in_deck % 4]
        return pokersuit + pokernumber
    
    def Poker2Num(self, poker: str, deck):
        num_in_deck = -1
        if poker[1] == "o":
            num_in_deck = 52
        elif poker[1] == "O":
            num_in_deck = 53
        else:
            num_in_deck = self.cardscale.index(poker[1])*4 + self.suitset.index(poker[0])
        if num_in_deck == -1:
            return -1
        if num_in_deck in deck:
            return num_in_deck
        return num_in_deck + 54
    
    
class Error(Exception):
    def __init__(self, ErrorInfo):
        self.ErrorInfo = ErrorInfo
    
    def __str__(self):
        return self.ErrorInfo  
    





