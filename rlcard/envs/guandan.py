from collections import Counter, OrderedDict
import numpy as np

from rlcard.envs import Env


class GuandanEnv(Env):
    ''' Guandan Environment
    '''

    def __init__(self, config):
        # from rlcard.games.doudizhu.utils import ACTION_2_ID, ID_2_ACTION
        from rlcard.games.doudizhu.utils import cards2str, cards2str_with_suit
        from rlcard.games.guandan import Game
        self._cards2str = cards2str
        self._cards2str_with_suit = cards2str_with_suit
        # self._ACTION_2_ID = ACTION_2_ID
        # self._ID_2_ACTION = ID_2_ACTION
        
        self.name = 'guandan'
        self.game = Game()
        super().__init__(config)
        self.state_shape = [[790], [901], [901]]# TODO
        self.action_shape = [[54] for _ in range(self.num_players)] # TODO

    def _extract_state(self, state):
        ''' Encode state

        Args:
            state (dict): dict of original state
        '''
        current_hand = _cards2array(state['current_hand'])
        others_hand = _cards2array(state['others_hand'])

        last_action = ''
        if len(state['trace']) != 0:
            if state['trace'][-1][1] == 'pass':
                last_action = state['trace'][-2][1] # TODO
            else:
                last_action = state['trace'][-1][1]
        last_action = _cards2array(last_action)

        last_9_actions = _action_seq2array(_process_action_seq(state['trace']))
        opponent_up = (state['self'] +3) %4
        opponent_down = (state['self'] +1) %4
        teammate = (state['self'] +2) %4
        opponent_up_played_cards = _cards2array(state['played_cards'][opponent_up])
        opponent_down_played_cards = _cards2array(state['played_cards'][opponent_down])
        teammate_played_cards = _cards2array(state['played_cards'][teammate])
        opponent_up_num_cards_left = _get_one_hot_array(state['num_cards_left'][opponent_up], 34) 
        opponent_down_num_cards_left = _get_one_hot_array(state['num_cards_left'][opponent_down], 34) 
        teammate_num_cards_left = _get_one_hot_array(state['num_cards_left'][teammate], 34) 

        obs = np.concatenate((current_hand,
                              others_hand,
                              last_action,
                              last_9_actions,
                              opponent_up_played_cards,
                              opponent_down_played_cards,
                              teammate_played_cards,
                              opponent_up_num_cards_left,
                              opponent_down_num_cards_left,
                              teammate_num_cards_left))
        
        extracted_state = OrderedDict({'obs': obs, 'legal_actions': self._get_legal_actions()})
        extracted_state['raw_obs'] = state
        extracted_state['raw_legal_actions'] = [a for a in state['actions']]
        extracted_state['action_record'] = self.action_recorder
        return extracted_state
            
    def get_payoffs(self):
        ''' Get the payoffs of players. Must be implemented in the child class.

        Returns:
            payoffs (list): a list of payoffs for each player
        '''
        return self.game.judger.judge_payoffs(self.game.round.landlord_id, self.game.winner_id)

    # def _decode_action(self, action_id):
    #     ''' Action id -> the action in the game. Must be implemented in the child class.

    #     Args:
    #         action_id (int): the id of the action

    #     Returns:
    #         action (string): the action that will be passed to the game engine.
    #     '''
    #     return self._ID_2_ACTION[action_id]

    def _get_legal_actions(self):
        ''' Get all legal actions for current state

        Returns:
            legal_actions (list): a list of legal actions
        '''
        legal_actions = self.game.state['actions']
        # legal_actions = {self._ACTION_2_ID[action]: _cards2array(action) for action in legal_actions}
        legal_actions = [ _cards2array(action) for action in legal_actions]
        return legal_actions

    def get_perfect_information(self):
        ''' Get the perfect information of the current state

        Returns:
            (dict): A dictionary of all the perfect information of the current state
        '''
        state = {}
        state['hand_cards_with_suit'] = [self._cards2str_with_suit(player.current_hand) for player in self.game.players]
        state['hand_cards'] = [self._cards2str(player.current_hand) for player in self.game.players]
        state['trace'] = self.game.state['trace']
        state['current_player'] = self.game.round.current_player
        state['legal_actions'] = self.game.state['actions']
        return state

    def get_action_feature(self, action):
        ''' For some environments such as DouDizhu, we can have action features

        Returns:
            (numpy.array): The action features
        '''
        return _cards2array(self._decode_action(action))

Card2Column = {'3': 0, '4': 1, '5': 2, '6': 3, '7': 4, '8': 5, '9': 6, 'T': 7,
               'J': 8, 'Q': 9, 'K': 10, 'A': 11, '2': 12}

NumOnes2Array = {0: np.array([0, 0, 0, 0, 0, 0, 0, 0]),
                 1: np.array([1, 0, 0, 0, 0, 0, 0, 0]),
                 2: np.array([1, 1, 0, 0, 0, 0, 0, 0]),
                 3: np.array([1, 1, 1, 0, 0, 0, 0, 0]),
                 4: np.array([1, 1, 1, 1, 0, 0, 0, 0]),
                 5: np.array([1, 1, 1, 1, 1, 0, 0, 0]),
                 6: np.array([1, 1, 1, 1, 1, 1, 0, 0]),
                 7: np.array([1, 1, 1, 1, 1, 1, 1, 0]),
                 8: np.array([1, 1, 1, 1, 1, 1, 1, 1])}
NumOnes2ArrayJ = {0: np.array([0, 0]),
                  1: np.array([1, 0]),
                  2: np.array([1, 1])}
def _cards2array(cards):
    if cards == 'pass':
        return np.zeros(108, dtype=np.int8)

    matrix = np.zeros([8, 13], dtype=np.int8)
    jokers = np.zeros(4, dtype=np.int8)
    counter = Counter(cards)
    for card, num_times in counter.items():
        if card == 'B':
            jokers[0:2] = NumOnes2ArrayJ[num_times]
        elif card == 'R':
            jokers[2:4] = NumOnes2ArrayJ[num_times]
        else:
            matrix[:, Card2Column[card]] = NumOnes2Array[num_times]
    return np.concatenate((matrix.flatten('F'), jokers))

def _get_one_hot_array(num_left_cards, max_num_cards):
    one_hot = np.zeros(max_num_cards, dtype=np.int8)
    one_hot[num_left_cards - 1] = 1

    return one_hot

def _action_seq2array(action_seq_list):
    action_seq_array = np.zeros((len(action_seq_list), 108), np.int8)
    for row, cards in enumerate(action_seq_list):
        action_seq_array[row, :] = _cards2array(cards)
    action_seq_array = action_seq_array.flatten()
    return action_seq_array

def _process_action_seq(sequence, length=9):
    sequence = [action[1] for action in sequence[-length:]]
    if len(sequence) < length:
        empty_sequence = ['' for _ in range(length - len(sequence))]
        empty_sequence.extend(sequence)
        sequence = empty_sequence
    return sequence
