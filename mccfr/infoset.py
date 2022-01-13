import numpy as np

class Infoset:

    def __init__(self, num_actions):
        self.cumul_regret = np.zeros(num_actions)
        self.cumul_strategy = np.zeros(num_actions)

    def get_strategy(self):
        """
        Gets current information set mixed strategy through regret-matching.
        """
        strategy = self.cumul_regret.clip(0)
        normalizing_sum = np.sum(strategy)
        if normalizing_sum > 0:
            return strategy / normalizing_sum
        return np.full_like(strategy, 1.0 / len(strategy))

    def get_average_strategy(self):
        """
        Gets average information set mixed strategy across all training iterations.
        """
        normalizing_sum = np.sum(self.cumul_strategy)
        if normalizing_sum > 0:
            return self.cumul_strategy / normalizing_sum
        return np.full_like(self.cumul_strategy, 1.0 / len(self.cumul_strategy))
