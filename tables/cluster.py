import numpy as np
from sklearn.cluster import KMeans
from os.path import exists
from hand_indexer import HandIndexer
from ochs_table import CARD_LIST
# import faiss

# TODO: consider using MiniBatchKMeans for speedup, or faiss library

CORES = 16
FLOP_BUCKETS = 256
TURN_BUCKETS = 256
RIVER_BUCKETS = 256

class Cluster:

    def __init__(self):
        indexer_2_3 = HandIndexer([2, 3])  # only needed for printing examples
        indexer_2_4 = HandIndexer([2, 4])
        indexer_2_5 = HandIndexer([2, 5])

        if not exists('flop_clusters.npy'):
            flopEquities = np.vstack([np.load('flop_equities' + str(i) + '.npy', allow_pickle=True) for i in range(CORES)])
            print('Running KMeans on flop equities, with size', flopEquities.shape)
            flopKMeansTrainer = KMeans(n_clusters=FLOP_BUCKETS, n_init=1, max_iter=1000000, random_state=42, verbose=1, tol=0).fit(flopEquities)
            flopKMeans = flopKMeansTrainer.labels_.astype(np.int8)
            
            # flopEquities = flopEquities.astype(np.float32)
            # flopKMeansTrainer = faiss.Kmeans(d=flopEquities.shape[1], k=FLOP_BUCKETS, niter=300, seed=42, verbose=True, max_points_per_centroid=1000000)
            # flopKMeansTrainer.train(flopEquities)
            # flopKMeans = flopKMeansTrainer.index.search(flopEquities, 1)[1]

            print(flopKMeans.shape)
            np.save('flop_clusters', flopKMeans)
            
            for clusterIdx in range(10):
                print('Cluster', clusterIdx)
                cluster = np.random.choice(np.where(flopKMeans == clusterIdx)[0], 10, replace=False)
                print(cluster)
                for i in cluster:
                    cards = [0] * 5
                    indexer_2_3.unindex(indexer_2_3.rounds - 1, i, cards)
                    readableCards = [CARD_LIST[c] for c in cards]
                    print(readableCards)

        if not exists('turn_clusters.npy'):
            turnEquities = np.vstack([np.load('turn_equities' + str(i) + '.npy', allow_pickle=True) for i in range(CORES)])
            print('Running KMeans on turn equities, with size', turnEquities.shape)
            turnKMeansTrainer = KMeans(n_clusters=TURN_BUCKETS, n_init=1, max_iter=1000000, random_state=42, verbose=1, tol=0).fit(turnEquities)
            turnKMeans = turnKMeansTrainer.labels_.astype(np.int8)

            print(turnKMeans.shape)
            np.save('turn_clusters', turnKMeans)
            
            for clusterIdx in range(10):
                print('Cluster', clusterIdx)
                cluster = np.random.choice(np.where(turnKMeans == clusterIdx)[0], 10, replace=False)
                print(cluster)
                for i in cluster:
                    cards = [0] * 6
                    indexer_2_4.unindex(indexer_2_4.rounds - 1, i, cards)
                    readableCards = [CARD_LIST[c] for c in cards]
                    print(readableCards)

        if not exists('river_clusters.npy'):
            riverEquities = np.vstack([np.load('river_equities' + str(i) + '.npy', allow_pickle=True) for i in range(CORES)]).astype(np.float32)
            print('Running KMeans on river equities, with size', riverEquities.shape)
            riverKMeansTrainer = KMeans(n_clusters=RIVER_BUCKETS, n_init=1, max_iter=1000000, random_state=42, verbose=1, tol=0).fit(riverEquities)
            riverKMeans = riverKMeansTrainer.labels_.astype(np.int8)

            print(riverKMeans.shape)
            np.save('river_clusters', riverKMeans)
            
            for clusterIdx in range(10):
                print('Cluster', clusterIdx)
                cluster = np.random.choice(np.where(riverKMeans == clusterIdx)[0], 10, replace=False)
                print(cluster)
                for i in cluster:
                    cards = [0] * 7
                    indexer_2_5.unindex(indexer_2_5.rounds - 1, i, cards)
                    readableCards = [CARD_LIST[c] for c in cards]
                    print(readableCards)