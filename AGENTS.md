# RLCard Development Guide

## Project Overview

RLCard is a toolkit for Reinforcement Learning (RL) in card games, developed by DATA Lab at Rice and Texas A&M University. It provides a unified framework for implementing and testing RL algorithms across various card games including Blackjack, Texas Hold'em, Dou Dizhu, UNO, Mahjong, Gin Rummy, Bridge, and Guandan.

**Key Features:**
- Multi-game support with standardized interfaces
- Built-in RL algorithms (DQN, NFSP, CFR, DMC)
- Human agent interfaces for interactive play
- PettingZoo integration for multi-agent reinforcement learning
- Comprehensive testing framework
- Pre-trained models available

## Technology Stack

- **Language**: Python 3.7+
- **Core Dependencies**: NumPy (≥1.16.3), termcolor
- **Optional Dependencies**: PyTorch, GitPython, matplotlib (for deep learning agents)
- **Testing**: pytest, unittest
- **CI/CD**: GitHub Actions

## Project Structure

```
rlcard/
├── __init__.py              # Package initialization and version info
├── agents/                  # RL algorithm implementations
│   ├── cfr_agent.py        # Counterfactual Regret Minimization
│   ├── dqn_agent.py        # Deep Q-Network
│   ├── nfsp_agent.py       # Neural Fictitious Self-Play
│   ├── dmc_agent/          # Deep Monte Carlo implementation
│   ├── human_agents/       # Human interfaces for various games
│   └── random_agent.py     # Random action baseline
├── envs/                   # Environment wrappers
│   ├── env.py              # Base environment class
│   ├── registration.py     # Environment registry
│   └── [game]_env.py       # Individual game environments
├── games/                  # Game logic implementations
│   ├── base.py             # Base game class
│   └── [game]/             # Individual game implementations
├── models/                 # Pre-trained model storage
├── utils/                  # Utility functions and helpers
```

## Build and Test Commands

### Installation
```bash
# Basic installation
pip install -e .

# With PyTorch support for deep learning agents
pip install -e .[torch]
```

### Testing
```bash
# Run all tests with coverage
py.test tests/ --cov=rlcard

# Run specific test modules
py.test tests/envs/test_blackjack_env.py
py.test tests/agents/test_dqn.py
```

### Running Examples
```bash
# Random agent baseline
python examples/run_random.py --env blackjack

# Deep Q-Learning
python examples/run_dqn.py --env blackjack

# CFR algorithm
python examples/run_cfr.py --env leduc-holdem

# Human play interface
python examples/human/blackjack_human.py
```

## Code Style Guidelines

### Naming Conventions
- **Classes**: PascalCase (e.g., `DQNAgent`, `BlackjackEnv`)
- **Functions/Methods**: snake_case (e.g., `get_legal_actions`, `extract_state`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_GAME_CONFIG`)
- **Private Methods**: Prefix with underscore (e.g., `_decode_action`)

### Code Organization
- Each game environment should inherit from `Env` base class
- Game logic should be separated from environment wrapper
- Agents should implement standard interfaces for training and inference
- Configuration should use `DEFAULT_GAME_CONFIG` pattern for game-specific settings

### Documentation
- Use docstrings for all public classes and methods
- Follow Google-style docstring format
- Include examples in docstrings for complex functions
- Comment complex game logic and algorithm implementations

## Testing Instructions

### Test Structure
- **Unit Tests**: Located in `tests/` mirroring source structure
- **Environment Tests**: Test game logic, state extraction, action decoding
- **Agent Tests**: Test algorithm implementations and training loops
- **Integration Tests**: Test full game playthroughs

### Writing Tests
- Use `unittest` framework for consistency
- Test deterministic behavior with `determinism_util.py`
- Include edge cases and boundary conditions
- Test both training and inference modes
- Verify action space and state space consistency

### Test Categories
1. **Environment Tests**: State extraction, action decoding, legal actions
2. **Game Logic Tests**: Rule enforcement, winner determination
3. **Agent Tests**: Training convergence, action selection
4. **Integration Tests**: Full game simulations

## Development Conventions

### Adding New Games
1. Implement game logic in `rlcard/games/[game]/`
2. Create environment wrapper in `rlcard/envs/[game]_env.py`
3. Register environment in `rlcard/envs/__init__.py`
4. Add comprehensive tests
5. Include example scripts
6. Update documentation

### Adding New Agents
1. Implement agent in `rlcard/agents/`
2. Follow existing agent interfaces
3. Include configuration parameters
4. Add training and inference methods
5. Write comprehensive tests
6. Provide example usage

### Configuration Management
- Use `DEFAULT_GAME_CONFIG` for game-specific settings
- Configuration keys should start with `game_`
- Support environment-level seeding
- Allow step-back functionality for planning algorithms

## Security Considerations

- Input validation for all user-provided configurations
- Safe handling of file I/O for model loading/saving
- Proper error handling in game logic to prevent crashes
- Validation of action spaces to prevent invalid moves
- Secure random number generation for game state

## Performance Guidelines

- Optimize state extraction for frequent calls
- Use efficient data structures for game state representation
- Implement vectorized operations where possible
- Profile training loops for bottleneck identification
- Consider memory usage for large-scale experiments

## Common Patterns

### Environment Interface
```python
# Standard environment creation
env = rlcard.make('game-name', config={'seed': 42})

# Agent setup
agent = SomeAgent(num_actions=env.num_actions)
env.set_agents([agent for _ in range(env.num_players)])

# Running episodes
trajectories, player_wins = env.run(is_training=False)
```

### State Representation
- Raw observations: Human-readable game state
- Processed observations: Numerical arrays for RL algorithms
- Legal actions: Mask or list of valid actions
- Action encoding: Integer mapping for discrete actions

### Agent Development
- Implement `train()` method for learning algorithms
- Implement `eval()` method for inference
- Support both training and evaluation modes
- Handle action masking for legal moves

## Debugging Tips

- Use `set_seed()` for reproducible results
- Enable verbose logging in examples
- Test with random agents first
- Use human interfaces for sanity checks
- Verify state extraction consistency
- Check action space boundaries

## Contributing Guidelines

1. Follow existing code style and patterns
2. Write comprehensive tests for new features
3. Update documentation for changes
4. Test across supported Python versions
5. Ensure CI/CD pipeline passes
6. Consider backward compatibility
7. Add examples for new features

For detailed contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).