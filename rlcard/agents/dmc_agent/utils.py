# Copyright 2021 RLCard Team of Texas A&M University
# Copyright 2021 DouZero Team of Kwai
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import traceback

import numpy as np
import torch

shandle = logging.StreamHandler()
shandle.setFormatter(
    logging.Formatter(
        '[%(levelname)s:%(process)d %(module)s:%(lineno)d %(asctime)s] '
        '%(message)s'))
log = logging.getLogger('doudzero')
log.propagate = False
log.addHandler(shandle)
log.setLevel(logging.INFO)

def get_batch(
    free_queue,
    full_queue,
    buffers,
    batch_size,
    lock
):
    with lock:
        indices = [full_queue.get() for _ in range(batch_size)]
    batch = {
        key: torch.stack([buffers[key][m] for m in indices], dim=1)
        for key in buffers
    }
    for m in indices:
        free_queue.put(m)
    return batch

def create_buffers(
    T,
    num_buffers,
    state_shape,
    action_shape,
    device_iterator,
):
    buffers = {}
    for device in device_iterator:
        buffers[device] = []
        for player_id in range(len(state_shape)):
            specs = dict(
                done=dict(size=(T,), dtype=torch.bool),
                episode_return=dict(size=(T,), dtype=torch.float32),
                target=dict(size=(T,), dtype=torch.float32),
                state=dict(size=(T,)+tuple(state_shape[player_id]), dtype=torch.int8),
                action=dict(size=(T,)+tuple(action_shape[player_id]), dtype=torch.int8),
            )
            _buffers = {key: [] for key in specs}
            for _ in range(num_buffers):
                for key in _buffers:
                    if device == "cpu":
                        _buffer = torch.empty(**specs[key]).to('cpu').share_memory_()
                    else:
                        _buffer = torch.empty(**specs[key]).to('cuda:'+str(device)).share_memory_()
                    _buffers[key].append(_buffer)
            buffers[device].append(_buffers)
    return buffers

def create_optimizers(
    num_players,
    learning_rate,
    momentum,
    epsilon,
    alpha,
    learner_model
):
    optimizers = []
    for player_id in range(num_players):
        optimizer = torch.optim.RMSprop(
            learner_model.parameters(player_id),
            lr=learning_rate,
            momentum=momentum,
            eps=epsilon,
            alpha=alpha)
        optimizers.append(optimizer)
    return optimizers

def act(
    i,
    device,
    T,
    free_queue,
    full_queue,
    model,
    buffers,
    env
):
    try:
        log.info('Device %s Actor %i started.', str(device), i)

        # Configure environment
        env.seed(i)
        all_agents = model.get_agents()

        done_buf = [[] for _ in range(env.num_players)]
        episode_return_buf = [[] for _ in range(env.num_players)]
        target_buf = [[] for _ in range(env.num_players)]
        state_buf = [[] for _ in range(env.num_players)]
        action_buf = [[] for _ in range(env.num_players)]
        size = [0 for _ in range(env.num_players)]

        while True:
            # 随机队友
            pos_to_agent = list(range(env.num_players))
            np.random.shuffle(pos_to_agent)
            current_agents = [all_agents[pos_to_agent[p]] for p in range(env.num_players)]
            env.set_agents(current_agents)

            trajectories, payoffs = env.run(is_training=True)

            for p in range(env.num_players):
                agent_id = pos_to_agent[p]
                size[agent_id] += len(trajectories[p][:-1]) // 2
                diff = size[agent_id] - len(target_buf[agent_id])
                if diff > 0:
                    done_buf[agent_id].extend([False for _ in range(diff-1)])
                    done_buf[agent_id].append(True)
                    episode_return_buf[agent_id].extend([0.0 for _ in range(diff-1)])
                    episode_return_buf[agent_id].append(float(payoffs[p]))
                    target_buf[agent_id].extend([float(payoffs[p]) for _ in range(diff)])
                    # State and action
                    for i in range(0, len(trajectories[p])-2, 2):
                        state = trajectories[p][i]['obs']
                        action = env.get_action_feature(trajectories[p][i+1])
                        state_buf[agent_id].append(torch.from_numpy(state))
                        action_buf[agent_id].append(torch.from_numpy(action))

                while size[agent_id] > T:
                    index = free_queue[agent_id].get()
                    if index is None:
                        break
                    for t in range(T):
                        buffers[agent_id]['done'][index][t, ...] = done_buf[agent_id][t]
                        buffers[agent_id]['episode_return'][index][t, ...] = episode_return_buf[agent_id][t]
                        buffers[agent_id]['target'][index][t, ...] = target_buf[agent_id][t]
                        buffers[agent_id]['state'][index][t, ...] = state_buf[agent_id][t]
                        buffers[agent_id]['action'][index][t, ...] = action_buf[agent_id][t]
                    full_queue[agent_id].put(index)
                    done_buf[agent_id] = done_buf[agent_id][T:]
                    episode_return_buf[agent_id] = episode_return_buf[agent_id][T:]
                    target_buf[agent_id] = target_buf[agent_id][T:]
                    state_buf[agent_id] = state_buf[agent_id][T:]
                    action_buf[agent_id] = action_buf[agent_id][T:]
                    size[agent_id] -= T

    except KeyboardInterrupt:
        pass
    except Exception as e:
        log.error('Exception in worker process %i', i)
        traceback.print_exc()
        print()
        raise e
