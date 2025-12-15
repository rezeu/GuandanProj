import unittest

import rlcard
from rlcard.agents.random_agent import RandomAgent
# from .determism_util import is_deterministic


class TestGuandanEnv(unittest.TestCase):

    def test_reset_and_extract_state(self):
        env = rlcard.make('guandan')
        state, _ = env.reset()
        self.assertEqual(state['obs'].size, 1722)

    # def test_is_deterministic(self):
    #     self.assertTrue(is_deterministic('guandan'))

    def test_get_legal_actions(self):
        env = rlcard.make('guandan')
        env.set_agents([RandomAgent(12345) for _ in range(env.num_players)])
        env.reset()
        legal_actions = env._get_legal_actions()
        self.assertLessEqual(len(legal_actions), 12345)

    def test_step(self):
        env = rlcard.make('guandan')
        _, player_id = env.reset()
        player = env.game.players[player_id]
        _, next_player_id = env.step('A',raw_action=True)
        self.assertEqual(next_player_id, (player.player_id+1)%len(env.game.players))

    def test_step_back(self):
        env = rlcard.make('guandan', config={'allow_step_back':True})
        _, player_id = env.reset()
        env.step('A',raw_action=True)
        _, back_player_id = env.step_back()
        self.assertEqual(player_id, back_player_id)
        self.assertEqual(env.step_back(), False)

        env = rlcard.make('guandan')
        with self.assertRaises(Exception):
            env.step_back()

    def test_run(self):
        env = rlcard.make('guandan')
        env.set_agents([RandomAgent(12345) for _ in range(env.num_players)])
        trajectories, payoffs = env.run(is_training=False)
        self.assertEqual(len(trajectories), 4)
        win = []
        for player_id, payoff in enumerate(payoffs):
            if payoff == 1:
                win.append(player_id)
        assert len(win)==2

    # def test_decode_action(self):
    #     env = rlcard.make('guandan')
    #     env.reset()
    #     env.game.state['actions'] = ['33366', '33355']
    #     env.game.judger.playable_cards[0] = ['5', '6', '55', '555', '33366', '33355']
    #     decoded = env._decode_action(3)
    #     self.assertEqual(decoded, '6')
    #     env.game.state['actions'] = ['444', '44466', '44455']
    #     decoded = env._decode_action(29)
    #     self.assertEqual(decoded, '444')

    def test_get_perfect_information(self):
        env = rlcard.make('guandan')
        _, player_id = env.reset()
        self.assertEqual(player_id, env.get_perfect_information()['current_player'])
if __name__ == '__main__':
    unittest.main()
