from eval7.handrange import HandRange
from sklearn.cluster import KMeans
import numpy as np
import eval7 as e7
import time
from multiprocessing import Process

# ranks = 
# suits = 
# cards = 


def gen_flops():
    hand = [e7.Card('Ac'), e7.Card('3d')]
    villain = HandRange("6Qs,7Ts,7Js,7Qs,8Ts,8Js,8Qs,8Ts,9Ts,9Js,9Qs,TJs,T9o,J8o,J9o,JTo,Q8o,Q9o,QTo,QJo")
    villainHand = [e7.Card('2d'), e7.Card('4c')]
    board = [e7.Card('Kh'), e7.Card('Ks'), e7.Card('2h'), e7.Card('Ad'), e7.Card('5s')]
    for _ in range(1400000):
        x = e7.py_hand_vs_range_exact(hand, villain, board)
        # x = e7.evaluate(hand + board) > e7.evaluate(villainHand + board)
    # for i in range(52):
    #     for j in range(52):
    #         for k in range(52):
    #             for l in range(52):
    #                 for m in range(52):
    #                     all_flops = [i, j, k, l, m]

if __name__ == '__main__':
    start = time.time()
    t1 = Process(target=gen_flops)
    t2 = Process(target=gen_flops)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print(time.time() - start)


# def to_canonical(): 
