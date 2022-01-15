import numpy as np
import time
import eval7 as e7
import math

CARD_LIST = ['2c', '2d', '2h', '2s', '3c', '3d', '3h', '3s', '4c', '4d', '4h', '4s', '5c', '5d', '5h', '5s', '6c', '6d', '6h', '6s', '7c', '7d', '7h', '7s', '8c', '8d', '8h', '8s', '9c', '9d', '9h', '9s', 'Tc', 'Td', 'Th', 'Ts', 'Jc', 'Jd', 'Jh', 'Js', 'Qc', 'Qd', 'Qh', 'Qs', 'Kc', 'Kd', 'Kh', 'Ks', 'Ac', 'Ad', 'Ah', 'As']
CARD_TO_E7 = [e7.Card(c) for c in CARD_LIST]
OPP_CLUSTERS = [
    e7.HandRange("23s,24s,25s,26s,27s,34s,35s,36s,37s,45s,46s,32o,43o,42o,54o,53o,52o,65o,64o,63o,62o,74o,73o,72o,83o,82o"),
    e7.HandRange("28s,29s,2Ts,38s,39s,47s,48s,49s,75o,85o,84o,95o,94o,93o,92o,T5o,T4o,T3o,T2o,J3o,J2o"),
    e7.HandRange("3Ts,4Ts,56s,57s,58s,59s,5Ts,67s,68s,69s,6Ts,78s,79s,89s,67o,68o,69o,6To,78o,79o,7To,89o,8To"),
    e7.HandRange("22,J2s,J3s,J4s,J5s,J6s,Q2s,Q3s,Q4s,Q5s,K2s,J4o,J5o,J6o,J7o,Q2o,Q3o,Q4o,Q5o,Q6o,Q7o,K2o,K3o,K4o"),
    e7.HandRange("6Qs,7Ts,7Js,7Qs,8Ts,8Js,8Qs,9Ts,9Js,9Qs,TJs,T9o,J8o,J9o,JTo,Q8o,Q9o,QTo,QJo"),
    e7.HandRange("33,44,55,K3s,K4s,K5s,K6s,K7s,K8s,A2s,A3s,A4s,A5s,A6s,K5o,K6o,K7o,K8o,K9o,A2o,A3o,A4o,A5o,A6o,A7o,A8o"),
    e7.HandRange("66,77,QTs,QJs,K9s,KTs,KJs,KQs,A7s,A8s,A9s,ATs,AJs,AQs,AKs,KTo,KJo,KQo,A9o,ATo,AJo,AQo,AKo"),
    e7.HandRange("88,99,TT,JJ,QQ,KK,AA"),
]


class OCHSTable:

    def __init__(self, indexer_2_3, indexer_2_4, indexer_2_5, pIdx):
        self.indexer_2_3 = indexer_2_3
        self.indexer_2_4 = indexer_2_4
        self.indexer_2_5 = indexer_2_5
        self.pIdx = pIdx

        indicesToCompute = math.ceil( 100 / 8 )
        flop_index_pair = (pIdx * indicesToCompute, min((pIdx + 1) * indicesToCompute, self.indexer_2_3.roundSize[1]))
        self.flop_equities = np.zeros((flop_index_pair[1] - flop_index_pair[0], len(OPP_CLUSTERS)))
        self.generate_flops(flop_index_pair)

        np.save('flop_equities' + str(pIdx), self.flop_equities)


    def generate_flops(self, index_pair):
        x = time.time()
        for i in range(*index_pair):
            cards = [0] * 5
            self.indexer_2_3.unindex(self.indexer_2_3.rounds - 1, i, cards)
            hand = [CARD_TO_E7[cards[0]], CARD_TO_E7[cards[1]]]
            deadCardMask = (1 << cards[0]) + (1 << cards[1]) + (1 << cards[2]) + (1 << cards[3]) + (1 << cards[4])
            equities = np.zeros(len(OPP_CLUSTERS))
            for turnCard in range(51):
                if ((1 << turnCard) & deadCardMask) != 0:
                    continue
                deadCardMask |= 1 << turnCard
                for riverCard in range(turnCard + 1, 52):
                    if ((1 << riverCard) & deadCardMask) != 0:
                        continue
                    board = [CARD_TO_E7[cards[2]], CARD_TO_E7[cards[3]], CARD_TO_E7[cards[4]], CARD_TO_E7[turnCard], CARD_TO_E7[riverCard]]
                    equities += [e7.py_hand_vs_range_exact(hand, oppCluster, board) for oppCluster in OPP_CLUSTERS]
            self.flop_equities[i - index_pair[0]] = equities / 1081
            if (i - index_pair[0]) % 1000 == 0:
                print(time.time() - x, self.pIdx)
                x = time.time()