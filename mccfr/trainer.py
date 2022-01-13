import numpy as np
from infoset import Infoset
from state import TerminalState

class Trainer:
    
    def __init__(self):
        self.node_map = {}  # infoset str -> infoset

    def __str__(self):
        output = ""
        for s, infoset in self.node_map.items():
            output += s + ": " + str(infoset.get_average_strategy()) + '\n'
        return output

    def cfr(self, state, traverser, t, prune=False):
        # TODO: chance sampling? combine traversers? update strategy only periodically / which turn?

        if isinstance(state, TerminalState):
            return state.deltas[traverser]

        actions = state.get_actions()  # TODO: store children in state to avoid recomputing states?

        infoset_str = state.get_infoset_str()
        infoset = self.node_map.get(infoset_str)
        if infoset is None:
            infoset = Infoset(len(actions))
            self.node_map[infoset_str] = infoset

        strategy = infoset.get_strategy()

        active = state.button % 2
        if traverser == active:
            utils = np.zeros(len(actions))

            # TODO: currently arbitrary bound, can also bound by strategy
            explore = infoset.regret > -100000 if prune and state.street != 5 else np.ones(len(actions), dtype=bool)
            for i in range(len(actions)):
                if explore[i]:
                    utils[i] = self.cfr(state.proceed(actions[i]), traverser, t, prune)

            node_util = np.dot(strategy, utils)
            regret = np.where(explore, utils - node_util, 0.)
            infoset.cumul_regret += regret
            return node_util

        else:
            i = np.random.choice(len(strategy), p=strategy)
            util = self.cfr(state.proceed(actions[i]), traverser, t, prune)
            infoset.cumul_strategy += strategy
            return util
