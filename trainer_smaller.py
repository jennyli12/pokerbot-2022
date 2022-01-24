import numpy as np
from infoset import Infoset
from state_smaller import TerminalState, get_first_action_states
from colorama import Fore, Style

REGRET_FLOOR = -110000
PRUNE_BOUND = -100000


class Trainer:

    def __init__(self, node_map):
        self.node_map = node_map

    def update_strategy(self, state, traverser):
        if isinstance(state, TerminalState):
            return

        actions = state.get_actions()

        active = state.button % 2
        if traverser == active:
            infoset_str = state.get_infoset_str()
            infoset = self.node_map.get(infoset_str)
            if infoset is None:
                infoset = Infoset(len(actions))
                self.node_map[infoset_str] = infoset

            strategy = infoset.get_strategy()

            i = np.random.choice(len(strategy), p=strategy)
            infoset.cumul_strategy[i] += 1
            self.update_strategy(state.proceed(actions[i]), traverser)

        else:
            for i in range(len(actions)):
                self.update_strategy(state.proceed(actions[i]), traverser)

    def cfr(self, state, traverser, prune=False):
        if isinstance(state, TerminalState):
            return state.deltas[traverser]

        actions = state.get_actions()

        infoset_str = state.get_infoset_str()
        infoset = self.node_map.get(infoset_str)
        if infoset is None:
            infoset = Infoset(len(actions))
            self.node_map[infoset_str] = infoset

        strategy = infoset.get_strategy()

        active = state.button % 2
        if traverser == active:
            utils = np.zeros(len(actions))

            explore = infoset.cumul_regret > PRUNE_BOUND if prune and state.street != 5 else np.ones(len(actions), dtype=bool)
            for i in range(len(actions)):
                if explore[i]:
                    utils[i] = self.cfr(state.proceed(actions[i]), traverser, prune)

            node_util = np.dot(strategy, utils)
            regret = np.where(explore, utils - node_util, 0.)
            infoset.cumul_regret += regret
            np.clip(infoset.cumul_regret, a_min=REGRET_FLOOR, a_max=None)
            return node_util

        else:
            i = np.random.choice(len(strategy), p=strategy)
            util = self.cfr(state.proceed(actions[i]), traverser, prune)
            # infoset.cumul_strategy += strategy
            return util

    def discount_infosets(self, d):
        for infoset in self.node_map.values():
            infoset.cumul_regret *= d
            infoset.cumul_strategy *= d

    def print_starting_hands_chart(self):
        states = get_first_action_states()
        actions = states[0].get_actions()
        for i in range(len(actions)):
            action = actions[i]
            print({'f': 'FOLD', 'c': 'CALL', 'x': 'RAISE0', 'y': 'RAISE1', 'z': 'RAISE2', 'a': 'ALL IN'}[action])
            print("    2    3    4    5    6    7    8    9    T    J    Q    K    A (suited)")
            for j in range(len(states)):
                state = states[j]

                infoset_str = state.get_infoset_str()
                infoset = self.node_map.get(infoset_str)
                if infoset is None:
                    infoset = Infoset(len(actions))
                    self.node_map[infoset_str] = infoset
                
                phi = infoset.get_average_strategy()

                if j % 13 == 0 and j + 1 < len(states):
                    if j // 13 < 8:
                        print(j // 13 + 2, " ", end='')
                    elif j // 13 == 8:
                        print("T  ", end='')
                    elif j // 13 == 9:
                        print("J  ", end='')
                    elif j // 13 == 10:
                        print("Q  ", end='')
                    elif j // 13 == 11:
                        print("K  ", end='')
                    else:
                        print("A  ", end='')

                string = "{:.2f}".format(phi[i]) + " "
                if phi[i] <= 0.25:
                    print(Fore.RED + string + Style.RESET_ALL, end='')
                elif phi[i] <= 0.5:
                    print(Fore.RED + Style.DIM + string + Style.RESET_ALL, end='')
                elif phi[i] <= 0.75:
                    print(Fore.GREEN + Style.DIM + string + Style.RESET_ALL, end='')
                else:
                    print(Fore.GREEN + string + Style.RESET_ALL, end='')
                
                if (j + 1) % 13 == 0:
                    print()
                
            print()
