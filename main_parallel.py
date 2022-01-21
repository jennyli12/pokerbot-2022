from trainer import Trainer
from state import get_root_state_parallel
import time
import random
import pickle
import numpy as np
from multiprocessing import Process


NUM_THREADS = 4
STRATEGY_INTERVAL = int(max(1, 1000 / NUM_THREADS))
PRUNE_THRESHOLD = 2e7 / NUM_THREADS
LCFR_THRESHOLD = 2e7 / NUM_THREADS
DISCOUNT_INTERVAL = int(1e6 / NUM_THREADS)
SAVE_TO_DISK_INTERVAL = int(1e6 / NUM_THREADS)
TEST_GAMES_INTERVAL = int(1e5 / NUM_THREADS)

BUCKETS = [['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88'],
           ['AKs', 'AKo', 'AQs', 'AQo', 'AJs', 'ATs', 'AJo', '77', '66', 'ATo',
            'A9s', 'A8s', 'KQs', 'A9o', 'A7s', 'KJs', 'KTs', 'KQo', 'KJo', 'QJs',
            'K9s', 'KTo', 'QTs'],
           ['55', '44', 'A5s', 'A8o', 'A6s', 'A4s', '33', 'A7o', 'A3s', 'A2s',
            'A5o', 'A6o', 'A4o', 'A3o', 'A2o', 'K8s', 'K7s', 'K9o', 'K6s', 'K5s',
            'K8o', 'K4s', 'K7o', 'K3s', 'K6o', 'K5o'],
           ['JTs', 'QJo', 'Q9s', 'QTo', 'Q8s', 'J9s', 'Q9o', 'JTo', 'Q7s', 'T9s',
            'Q6s', 'J8s', 'Q8o', 'J9o', 'T8s', 'J7s', 'J8o', 'T9o', 'T7s'],
           ['22', 'K2s', 'K4o', 'K3o', 'Q5s', 'K2o', 'Q4s', 'Q3s', 'Q7o', 'Q2s',
            'Q6o', 'Q5o', 'J6s', 'J5s', 'Q4o', 'J4s', 'J7o', 'Q3o', 'J3s', 'Q2o',
            'J2s', 'J6o', 'J5o', 'J4o'],
           ['98s', '97s', 'T8o', 'T6s', '87s', '98o', 'T7o', '96s', 'T5s', 'T4s',
            '86s', 'T6o', '97o', 'T3s', '76s', '95s', '87o', '85s', '96o', '75s',
            '65s', '86o', '76o'],
           ['J3o', 'T2s', 'T5o', 'J2o', '94s', 'T4o', '93s', '84s', '95o', 'T3o',
            '92s', '74s', 'T2o', '85o', '83s', '94o', '75o', '82s', '93o', '84o',
            '92o'],
           ['54s', '64s', '73s', '65o', '53s', '63s', '43s', '74o', '72s', '54o',
            '64o', '52s', '62s', '83o', '42s', '82o', '73o', '53o', '63o', '32s',
            '43o', '72o', '52o', '62o', '42o', '32o']]


def train(pidx, possible_hands):
    node_map = {}
    trainer = Trainer(node_map)
    
    start_time = time.perf_counter()
    t = 1
    while True:
        if t % 1000 == 0:
            d = time.perf_counter() - start_time
            print('Thread', pidx, '| Iters', t, '| Iters/s', "{:.2f}".format(t / d), '| Min', "{:.2f}".format(d / 60), '| Infosets', len(node_map))
        # if t % TEST_GAMES_INTERVAL == 0:
        #     trainer.print_starting_hands_chart()
        #     # TODO: play test games
        for traverser in [0, 1]:  # SB, BB
            if t % STRATEGY_INTERVAL == 0:
                trainer.update_strategy(get_root_state_parallel(traverser, possible_hands), traverser)
            if t > PRUNE_THRESHOLD and random.random() < 0.95:
                trainer.cfr(get_root_state_parallel(traverser, possible_hands), traverser, True)
            else:
                trainer.cfr(get_root_state_parallel(traverser, possible_hands), traverser)
        if t % SAVE_TO_DISK_INTERVAL == 0:
            print("SAVING")
            node_map_save = {}
            avg_strategy_save = {}
            for s, infoset in node_map.items():
                node_map_save[s] = np.concatenate((infoset.cumul_regret, infoset.cumul_strategy))
                avg_strategy_save[s] = infoset.get_average_strategy()
            with open(f'nodemap{pidx}.pickle', 'wb') as f:
                pickle.dump(node_map_save, f, protocol=pickle.HIGHEST_PROTOCOL)
            with open(f'avgstrategy{pidx}.pickle', 'wb') as f:
                pickle.dump(avg_strategy_save, f, protocol=pickle.HIGHEST_PROTOCOL)
        if t < LCFR_THRESHOLD and t % DISCOUNT_INTERVAL == 0:
            d = (t / DISCOUNT_INTERVAL) / (t / DISCOUNT_INTERVAL + 1)
            trainer.discount_infosets(d)
        t += 1


if __name__ == "__main__":  
    alloc = [[] for _ in range(NUM_THREADS)]
    proc, inc = 0, 1
    for bucket in BUCKETS:
        for hand in bucket:
            alloc[proc].append(hand)
            proc += inc
            if proc == -1:
                proc += 1
                inc = 1
            elif proc == NUM_THREADS:
                proc -= 1
                inc = -1

    processes = []
    for pidx in range(NUM_THREADS):
        p = Process(target=train, args=(pidx, alloc[pidx]))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
