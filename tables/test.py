from hand_indexer import HandIndexer
from ochs_table import OCHSTable
from multiprocessing import Process


def main_process(pIdx):
    indexer_2_3 = HandIndexer([2, 3])
    indexer_2_4 = HandIndexer([2, 4])
    indexer_2_5 = HandIndexer([2, 5])
    OCHSTable(indexer_2_3, indexer_2_4, indexer_2_5, pIdx)


if __name__ == '__main__':
    processes = []
    for i in range(8):
        p = Process(target=main_process, args=(i,))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
    