# DMC训练流程与对手机制

## 训练流程（核心4阶段）

### 阶段1：初始化
```python
env = rlcard.make('guandan-v2')
model = DMCModel(state_shape=[[1722]*4], action_shape=[[143]*4])
env.set_agents(model.get_agents())  # 关键：4个玩家使用同一模型的不同副本
```

### 阶段2：数据收集（并行Actor）
- 启动多个actor进程（默认1-5个）
- 每个actor独立运行`env.run(is_training=True)`
- 收集trajectory：(state, action, reward)
- 编码并存储到共享buffers

### 阶段3：学习（异步Learner）
- Learner线程从buffers采样batch
- 对每个玩家：计算loss → backward → optimizer.step()
- 将更新后的模型参数同步到所有actor

### 阶段4：检查点
- 每`save_interval`分钟保存模型
- 同时保存优化器状态和训练统计

## 对手机制详解

### 默认：Self-Play（自我对弈）

**实现方式**：
```python
# 这不是4个不同模型，而是同一个模型的4个副本
env.set_agents([
    model.get_agent(0),  # 玩家0使用模型(参数相同)
    model.get_agent(1),  # 玩家1使用同一模型(独立前向)
    model.get_agent(2),  # 玩家2使用同一模型(独立前向)
    model.get_agent(3),   # 玩家3使用同一模型(独立前向)
])
```

**核心特点**：
- 4个玩家共享**同一网络权重**
- 但各自**独立前向传播**选择动作
- 训练目标：让这个模型能击败它自己

**优势**：
- ✅ 自动匹配对手水平
- ✅ 无需管理对手池
- ✅ 计算资源高效
- ✅ 收敛稳定

**Self-Play类比**：
- 就像AlphaGo通过和自己下棋来学习
- 或者你通过反复研究自己的对局来提高

### RandomAgent的作用

**Self-Play不需要RandomAgent初始化！**

RandomAgent的用途：

**1. 环境测试**（开发阶段）
```python
# 快速验证环境是否正常工作
env = GuandanEnv()
agents = [RandomAgent() for _ in range(4)]
env.set_agents(agents)
trajectories, payoffs = env.run()  # 应该能正常运行
```

**2. 基线对比**（评估阶段）
```python
# 训练后模型 vs 随机agent = 性能度量
trained_model = load_model('checkpoint.tar')
env.set_agents([trained_model.get_agent(0)] + [RandomAgent()]*3)
results = evaluate(env, num_games=1000)
print(f"vs Random得分: {np.mean(results)}")  # 应该接近1.0
```

**3. 不是训练对手**
- DMC训练时不需要RandomAgent
- Self-Play从随机初始化开始学习
- RandomAgent太弱，无法提供有效训练信号

### 为什么不需要RandomAgent初始化？

DMC的Self-Play机制：
1. **初始模型**：权重随机初始化 → 表现像随机agent
2. **自我对弈**：4个随机模型对局 → 收集经验
3. **学习改进**：Learner从经验中学习 → 模型逐渐变强
4. **循环迭代**：更强的模型对弈 → 更高质量经验

这个过程会自动产生从弱到强的完整学习曲线。

## 推荐训练流程

### 步骤1：环境验证（5分钟）
```python
# 快速测试环境
env = GuandanEnv()
agents = [RandomAgent() for _ in range(4)]
env.set_agents(agents)

# 运行10局游戏，检查是否崩溃
for i in range(10):
    trajectories, payoffs = env.run()
    print(f"Game {i}: OK")
```

### 步骤2：正式训练（1-2天）
```bash
# 使用SELF-PLAY训练（关键！）
python ./examples/run_dmc.py \
    --env guandan-v2 \
    --xpid my_training \
    --num_actor_devices 2 \
    --num_actors 3 \
    --save_interval 60
```

### 步骤3：性能评估（30分钟）
```python
# 加载训练模型
trained_model = load_model('my_training/model.tar')

# 测试1: Self-play性能
env.set_agents([trained_model]*4)
self_play_results = evaluate(env, num_games=1000)
print(f"Self-play性能: {np.mean(self_play_results)}")

# 测试2: vs Random性能
env.set_agents([trained_model.get_agent(0)] + [RandomAgent()]*3)
vs_random_results = evaluate(env, num_games=1000)
print(f"vs Random性能: {np.mean(vs_random_results)}")

# 测试3: 混合性能
env.set_agents([trained_model.get_agent(0), RandomAgent(), 
                trained_model.get_agent(2), RandomAgent()])
mix_results = evaluate(env, num_games=1000)
print(f"混合性能: {np.mean(mix_results)}")
```

预期性能：
- Self-play: ~0.0（势均力敌）
- vs Random: ~0.9（碾压级优势）
- Mixed: ~0.5（合理优势）

### 步骤4：超参数调优（可选）
```bash
# 网格搜索超参数
hyperparams = [
    ("lr_1e4_eps_01", 0.0001, 0.01),
    ("lr_5e4_eps_05", 0.0005, 0.05),
]

for name, lr, eps in hyperparams:
    python run_dmc.py \
        --xpid $name \
        --learning_rate $lr \
        --exp_epsilon $eps
```

## DMC vs 其他训练方法

| 方法 | 对手 | 速度 | 性能 | 适用|
|------|------|------|------|-----|
| **DMC** | Self-Play | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ 推荐 |
| DQN | Random | ⭐⭐ | ⭐⭐ |
| PPO | Self-Play | ⭐⭐⭐ | ⭐⭐⭐⭐ | 可选 |
| A3C | Random | ⭐⭐⭐⭐ | ⭐⭐ | |

## 训练监控

### 关键指标
```bash
tail -f experiments/dmc_result/my_training/out.log

# 期望看到：
[INFO] After 12800 frames: @ 1300.0 fps Stats:
{
  'mean_episode_return_0': 0.25,   # 开始分化
  'loss_0': 0.95,                  # 逐步下降
  'mean_episode_return_1': -0.25,  # 对手
  'loss_1': 0.92,
  ...
}
```

### 收敛标准
- **早期**（< 10万帧）：loss ~1.0，奖励波动
- **中期**（10-100万帧）：loss ~0.5-0.8，奖励开始分化
- **后期**（> 100万帧）：loss ~0.2-0.5，奖励接近±1.0

### 理想最终性能
```
mean_episode_return: 0.8 ~ 0.95  （获胜方）
loss: 0.1 ~ 0.3                    （收敛）
```

## 常见问题

### Q1: 能直接用RandomAgent训练吗？
A: **不能**。RandomAgent太弱，无法提供有效学习信号。必须使用Self-Play。

### Q2: 训练多久才能看到效果？
A: **至少10-50万帧**（几小时到1天）。完整训练需要100万+帧（1-2天）。

### Q3: 如何判断训练成功？
A: 两个指标：
- loss持续下降并稳定
- mean_episode_return趋向±1.0（队伍分化）

### Q4: 需要多个GPU吗？
A: **不是必须的**，但推荐：
- CPU: 训练慢但可行
- 单GPU: 平衡选择
- 多GPU: 加速训练

### Q5: RandomAgent有什么用？
A: **仅用于**：
1. 开发阶段：快速测试环境
2. 评估阶段：基线对比
3. **不是**训练对手

---

## 核心结论

**重要区别**：
- **Self-Play**：训练时使用（agent vs agent）
- **RandomAgent**：评估时使用（agent vs 随机）

**训练命令**：
```bash
# ✅ 正确：Self-Play训练
python run_dmc.py --env guandan-v2 --xpid train

# ❌ 错误：不能用RandomAgent训练
python run_dmc.py --env guandan-v2 --xpid wrong --use_random
```

**推荐流程**：
1. 用RandomAgent**快速测试环境**（5分钟）
2. 用Self-Play**正式训练**（1-2天）
3. 用RandomAgent**评估性能**（30分钟）
4. **享受训练好的模型**