from collections import Counter, OrderedDict
import numpy as np

from rlcard.envs.env import Env


class GuandanEnv(Env):
    ''' Guandan Environment
    '''

    def __init__(self, config):
        from rlcard.games.guandan.game import Game
        self.name = 'guandan'
        self.game = Game()
        super().__init__(config)
        self.state_shape = [[2284], [2284], [2284],[2284]]# TODO
        self.action_shape = [[216] for _ in range(self.num_players)] # TODO

    def _extract_state(self, state):
        ''' Encode state

        Args:
            state (dict): dict of original state
        '''


        obs = state['obs']

            # obs_set[i] = {
            #     "id": i,      1
            #     "level": self.level,              1
            #     "deck": self.player_decks[i],     108
            #     "history": self.history,          (1 + 108 + 108) * 10
            # }
            # response = {
            #     'player': -1, # the first round
            #     'response': [[],[]] 
            #     }

        history_encoding = []
        for i in range(10):
            if len(obs['history']) > i:
                # 如果有足够的历史记录，添加最近的第i条记录
                history_item = obs['history'][-(i+1)]  # 从最近的一条开始
                history_encoding.extend(
                    [history_item['player']] + 
                    self.Num2vector(history_item['response'][0]) +
                    self.Num2vector(history_item['response'][1])
                )
            else:
                # 如果历史记录不足，用默认值填充
                history_encoding.extend([-1] + [0 for _ in range(108)] + [0 for _ in range(108)])

        cardscale = ['A','2','3','4','5','6','7','8','9','0','J','Q','K']
        level_index = cardscale.index(obs['level']) if obs['level'] in cardscale else -1

        last_card_num = [27,27,27,27]
        for history_item in obs['history']:
            if history_item['player'] != -1:
                last_card_num[history_item['player']] -= len(history_item['response'][0])

        extracted_obs = np.concatenate([
            np.array([obs['id']]),   
            np.array([last_card_num[i] for i in range(4)]),
            np.array([level_index]),
            np.array(self.Num2vector(obs['deck'])),
            np.array(history_encoding)
        ])

        legal_actions = state['legal_actions']

        extracted_legal_actions = np.array([self.Num2vector(legal_action['response'][0]) + self.Num2vector(legal_action['response'][1]) for legal_action in legal_actions] )
        if(len(extracted_legal_actions) == 0):
            extracted_legal_actions = np.array([[0 for _ in range(216)]])

        dict_legal_actions = {}
        
       

        for i in range(len(extracted_legal_actions)):
            dict_legal_actions[i] = extracted_legal_actions[i]
        extracted_state = OrderedDict({'obs': extracted_obs, 'legal_actions': dict_legal_actions})
        
        # 未实现
        # extracted_state['raw_obs'] = state
        # extracted_state['raw_legal_actions'] = [a for a in state['actions']]
        # extracted_state['action_record'] = self.action_recorder
        
        return extracted_state
            
    def get_payoffs(self):
        ''' Get the payoffs of players. Must be implemented in the child class.

        Returns:
            payoffs (list): a list of payoffs for each player
        '''
        return self.game.reward

    def _decode_action(self, response):
        action = response[:108]
        claim = response[108:]
        action = [i for i in range(108) if action[i] == 1]
        claim = [i for i in range(108) if claim[i] == 1]
        return {'player':self.game.current_player,'response': [ action, claim ]} 

    def Num2vector(self, num: list):

        return [1 if i in num else 0 for i in range(108)]