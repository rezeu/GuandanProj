import json
import sys
import traceback
import torch
from rlcard.agents.dmc_agent.model import DMCAgent

# 导入自定义的环境和游戏类
from rlcard.envs.guandan import GuandanEnv
from rlcard.games.guandan.game import Game
mystr = ""
class GuandanBot:
    def __init__(self, your_id, level, initial_deck):
        """初始化bot"""
        self.your_id = your_id
        self.level = level
        
        # 初始化游戏状态
        self.game = Game()
        config = {'level': level, 'seed': None, 'allow_step_back': False}
        self.game.init_game(config)
        
        # 设置当前玩家的手牌
        self.game.player_decks[your_id] = initial_deck
        
        # 初始化环境
        self.env = GuandanEnv({'allow_step_back': False,'seed':None})
        self.env.game = self.game
        
        # 初始化DMCAgent
        state_shape = [[2280], [2280], [2280], [2280]]
        action_shape = [[216] for _ in range(4)]
        
        # 这里需要加载训练好的模型，这里用随机策略作为示例
        # 实际使用时应加载训练好的模型权重
        self.agent = DMCAgent(
            state_shape=state_shape[your_id],
            action_shape=action_shape[your_id],
            mlp_layers=[512, 512, 512, 512, 512],
            exp_epsilon=0.01,
            device="cpu"
        )
        model_path = f"data/0_0.pth"
        self.agent = torch.load(model_path, map_location='cpu')
        self.agent.eval()
        # 设置agent为评估模式
        
    def update_history(self, historys):
        """更新游戏状态"""
        lastmove = {"player": -1, "response": [[],[]]}


        for i in range(4): #截断本回合
            if historys[-i-1] == []:
                continue
            if historys[-i-1]['player'] != self.your_id:
                continue
            historys = historys[-i-1:]
            break

        for history in historys:
            if history == []:
                continue

            if history["player"] != -1 and history["response"] != [[],[]]:
                lastmove = {"player": history["player"], "response": history["response"]}
            self.game.history.append(history)

            if history["player"] == self.your_id:  #更新自己手牌
                self.update_deck_after_action(history)

        if lastmove["player"] == self.your_id: #上次是自己
            lastmove = {"player": -1, "response": [[],[]]}
        # 更新最后一步
        self.game.lastMove = lastmove

    def get_action(self):
        """获取动作"""
        # 获取当前状态
        state = self.game.get_state(self.your_id)
        #mystr += "state: " + str(state) + "\n"
        # 提取状态（使用环境的方法）
        extracted_state = self.env._extract_state(state)
        #mystr += "extracted_state: " + str(extracted_state) + "\n"
        # 使用agent选择动作
        action_values, info = self.agent.eval_step(extracted_state)
        #mystr += "action_values: " + str(action_values) + "\n"
        # 解码动作
        action = self.env._decode_action(action_values)
        #mystr += "action: " + str(action) + "\n"
        return action
    
    def update_deck_after_action(self, action):
        """执行动作后更新手牌"""
        if action['response'][0]:  # 如果不是pass
            # 从手牌中移除打出的牌
            for card in action['response'][0]:
                if card in self.game.player_decks[self.your_id]:
                    self.game.player_decks[self.your_id].remove(card)

if __name__ == '__main__':
    try:
        # 读取输入
        input_data = sys.stdin.readline()
        data = json.loads(input_data)
        
        # 获取初始信息
        round_num = 0

        requests = data.get('requests', [])
        request = requests[round_num]
        round_num += 1

        deck = request['deliver']
        your_id = request['your_id']
        global_dict = request['global']
        level = global_dict['level']
        
        # 创建bot
        bot = GuandanBot(your_id, level, deck)

        if len (requests) == 1:
            response = {"response": [],"debug":"??"}
            print(json.dumps(response))
            sys.stdout.flush()
            sys.exit(0)
        
        # 主循环
        while round_num < len(requests):
            request = requests[round_num]
            round_num += 1
            historys = request['history']  # 4个历史记录

            bot.update_history(historys)
            
        

        # 获取动作
        action = bot.get_action()
        # 更新手牌
        bot.update_deck_after_action(action)
        
        # 输出动作   
        response = {"response": action["response"],"debug" : "????" }
        print(json.dumps(response))
        sys.stdout.flush()
            
    except Exception as e:
        error_msg = {
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        print(json.dumps(error_msg))
        sys.stdout.flush()



