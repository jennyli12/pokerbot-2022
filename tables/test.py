from operator import index
from hand_indexer import HandIndexer
from ochs_table import OCHSTable

if __name__ == '__main__':
    indexer_2_3 = HandIndexer([2, 3])
    print(indexer_2_3.roundSize[1])
    indexer_2_4 = HandIndexer([2, 4])
    print(indexer_2_4.roundSize[1])
    indexer_2_5 = HandIndexer([2, 5])
    print(indexer_2_5.roundSize[1])

    tbl = OCHSTable(indexer_2_3, indexer_2_4, indexer_2_5)
