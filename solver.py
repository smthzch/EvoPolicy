import os
import json
import numpy as np
import matplotlib.pyplot as plt

from tqdm import tqdm

from network import EvoNetwork

class EvoSolver:
    def __init__(self, env, nhidden=1, hidden_width=12, activation='tanh', selection='max'):
        selections = ['max', 'random']
        if selection not in selections:
            raise ValueError(f'selection must be one of {selections}')
            
        self.env = env
        self.action_space = self.env.action_space.n
        self.state_space = 1
        #flatten observation space
        for i in range(len(self.env.observation_space.shape)):
            self.state_space *= self.env.observation_space.shape[i]
        
        self.selection = selection
        self.policy_net = EvoNetwork(
                self.state_space,
                hidden_width,
                self.action_space,
                nhidden=nhidden,
                activation=activation
            )
        
        self.times = []
        self.rewards = []
    
    def pathfind(self, particle=None, limit=None):
        state = self.env.reset()
        state = state.reshape((1, self.state_space))
        self.path = dict(
                actions=[],
                rewards=[],
                time=0
            )
        
        done = False
        i = 0
        while not done:
            if i==limit:
                break
            action = self.selectAction(state, particle)
            next_state, reward, done, _ = self.env.step(action)
            self.path['actions'] += [action]
            self.path['rewards'] += [reward]
            self.path['time'] += 1
            state = next_state.reshape((1, self.state_space))
            i+=1
            
    def train(self, 
              neps=100, 
              lr=1e-1, 
              sigma=1e-1, 
              batch_size=10, 
              nparticles=10,
              decay=1,
              decay_step=1e6,
              step_method='weighted',
              limit=None,
              infofile=None,
              modpath=None,
              plot=False):
        trng = tqdm(range(neps))

        for i_episode in trng:
            if (i_episode+1)%decay_step == 0:
                lr *= decay 
                sigma *= decay 
            
            self.policy_net.jitter(sigma, nparticles)
            
            ep_rewards = []
            ep_times = []
            best_time = float('inf')
            for i in range(nparticles):
                part_rewards = []
                part_times = []
                while len(part_rewards) < batch_size:
                    self.pathfind(i, limit=limit)
                    part_rewards += [sum(self.path['rewards'])]
                    part_times += [self.path['time']]
                
                ep_rewards += [sum(part_rewards)]
                part_time = sum(part_times)/len(part_times)
                ep_times += [part_time]
                if part_time > best_time:
                    best_time = part_time
                    
            self.times += [sum(ep_times)/len(ep_times)]
            self.rewards += [sum(ep_rewards)/len(ep_rewards)]
            
            self.policy_net.step(ep_rewards, lr, step_method)
            
            if infofile is not None:
                with open(infofile, 'w') as wrt:
                    json.dump({
                                'times': self.times,
                                'rewards': self.rewards
                                },
                                wrt)
            if plot: 
                plt.plot(self.times)
                plt.show()
                plt.pause(0.001)
                    
            trng.set_description(f'Time: {round(self.times[-1], 2)}')
            
        if infofile is not None:
            with open(infofile, 'w') as wrt:
                json.dump({
                            'times': self.times,
                            'rewards': self.rewards
                            },
                            wrt)
        
    
    def selectAction(self, state, particle=None):
        if particle is not None:
            act = self.policy_net.forwardParticle(particle, state)[0]
        else:
            act = self.policy_net.forward(state)[0]
        if self.selection=='max':
            action = act.argmax()
        else: #random
            action = np.random.choice(self.action_space, p=act)
        return action
    
    def save(self, file_path):
        model = self.policy_net.dump()
        policy = dict(
                selection=self.selection,
                state_space=self.state_space,
                action_space=self.action_space,
                model=model
            )
        with open(file_path, 'w') as wrt:
            json.dump(policy, wrt)
            
    def load(self, file_path):
        with open(file_path, 'r') as rd:
            policy = json.load(rd)
        self.policy_net.load(policy['model'])
        self.selection = policy['selection']
        self.state_space = policy['state_space']
        self.action_space = policy['action_space']
    