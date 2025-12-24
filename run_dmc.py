''' An example of training a Deep Monte-Carlo (DMC) Agent on the environments in RLCard
'''
import os
import argparse

import torch

from rlcard.envs.guandan import GuandanEnv
from rlcard.agents.dmc_agent import DMCTrainer

def train(args):

    # Make the environment
    config = {
        'allow_step_back': False,
        'seed': None,
        # 可以根据需要添加其他配置项
    }
    env = GuandanEnv(config)

    # Initialize the DMC trainer
    print(args.load_model)
    trainer = DMCTrainer(
        env,
        cuda=args.cuda,
        load_model=args.load_model,
        xpid=args.xpid,
        savedir=args.savedir,
        save_interval=args.save_interval,
        num_actor_devices=args.num_actor_devices,
        num_actors=args.num_actors,
        training_device=args.training_device,
    )

    # Train DMC Agents
    trainer.start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser("DMC example in RLCard")
    parser.add_argument(
        '--env',
        type=str,
        default='guandan',
        choices=[
            'guandan'
        ],
    )
    parser.add_argument(
        '--cuda',
        type=str,
        default='',
    )
    parser.add_argument(
        '--load_model',
        action='store_true',
        default= True,
        help='Load an existing model',
    )
    parser.add_argument(
        '--xpid',
        default='guandan',
        help='Experiment id (default: guandan)',
    )
    parser.add_argument(
        '--savedir',
        default='experiments/dmc_result',
        help='Root dir where experiment data will be saved'
    )
    parser.add_argument(
        '--save_interval',
        default=30,
        type=int,
        help='Time interval (in minutes) at which to save the model',
    )
    parser.add_argument(
        '--num_actor_devices',
        default=1,
        type=int,
        help='The number of devices used for simulation',
    )
    parser.add_argument(
        '--num_actors',
        default=1,
        type=int,
        help='The number of actors for each simulation device',
    )
    parser.add_argument(
        '--training_device',
        default="0",
        type=str,
        help='The index of the GPU used for training models',
    )

    args = parser.parse_args()

    os.environ["CUDA_VISIBLE_DEVICES"] = args.cuda
    train(args)

