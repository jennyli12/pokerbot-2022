from trainer import Trainer
from state import get_root_state
import time
import random
import pickle
import numpy as np


NUM_THREADS = 1
STRATEGY_INTERVAL = int(max(1, 1000 / NUM_THREADS))
PRUNE_THRESHOLD = 2e7 / NUM_THREADS
LCFR_THRESHOLD = 2e7 / NUM_THREADS
DISCOUNT_INTERVAL = int(1e6 / NUM_THREADS)
SAVE_TO_DISK_INTERVAL = int(5e5 / NUM_THREADS)
TEST_GAMES_INTERVAL = int(1e5 / NUM_THREADS)


if __name__ == "__main__":

    node_map = {}
    trainer = Trainer(node_map)
    
    start_time = time.perf_counter()
    t = 1
    while True:
        if t % 1000 == 0:
            print('Training iterations', t)
            print('Iterations per second', t / (time.perf_counter() - start_time))
            print('Minutes running', (time.perf_counter() - start_time) / 60)
            print('Infosets', len(node_map))
            print()
        if t % TEST_GAMES_INTERVAL == 0:
            trainer.print_starting_hands_chart()
            # TODO: play test games
        for traverser in [0, 1]:  # SB, BB
            if t % STRATEGY_INTERVAL == 0:
                trainer.update_strategy(get_root_state(), traverser)
            if t > PRUNE_THRESHOLD and random.random() < 0.95:
                trainer.cfr(get_root_state(), traverser, True)
            else:
                trainer.cfr(get_root_state(), traverser)
        if t % SAVE_TO_DISK_INTERVAL == 0:
            print("SAVING")
            node_map_save = {}
            avg_strategy_save = {}
            for s, infoset in node_map.items():
                node_map_save[s] = np.concatenate((infoset.cumul_regret, infoset.cumul_strategy))
                avg_strategy_save[s] = infoset.get_average_strategy()
            with open('nodemap.pickle', 'wb') as f:
                pickle.dump(node_map_save, f, protocol=pickle.HIGHEST_PROTOCOL)
            with open('avgstrategy.pickle', 'wb') as f:
                pickle.dump(avg_strategy_save, f, protocol=pickle.HIGHEST_PROTOCOL)
        if t < LCFR_THRESHOLD and t % DISCOUNT_INTERVAL == 0:
            d = (t / DISCOUNT_INTERVAL) / (t / DISCOUNT_INTERVAL + 1)
            trainer.discount_infosets(d)
        t += 1

    # preflop = set()
    # postflop = set()
    # for s, infoset in node_map.items():
    #     idx1 = s.find('P')
    #     # idx2 = s.find('R')
    #     if idx1 != -1:
    #         preflop.add(s[:idx1])
    #     # if idx2 != -1:
    #     #     postflop.add(s[:idx2])
    # print(preflop, postflop)

    # output = ""
    # for s, infoset in node_map.items():
    #     output += s + ": " + str(infoset.get_average_strategy()) + '\n'
    # print(output)
