import numpy as np
import math
from ctypes import *
from os.path import exists

def number_of_trailing_zeros(n):
        mask = 1
        for i in range(32):
            if (n & mask) != 0:
                return i
            mask <<= 1
        return 32


def pop_count(n):
    return bin(n).count('1')


def swap(suitIndex, u, v):
    if suitIndex[u] > suitIndex[v]:
        suitIndex[u], suitIndex[v] = (suitIndex[v], suitIndex[u])


class GetOutOfLoop(Exception):
    pass


class HandIndexerState:
    def __init__(self):
        self.suitIndex = np.zeros(HandIndexer.SUITS, dtype=int)
        self.suitMultiplier = np.ones(HandIndexer.SUITS, dtype=int)
        self.round = 0
        self.permutationIndex = 0
        self.usedRanks = np.zeros(HandIndexer.SUITS, dtype=int)
        self.permutationMultiplier = 1


class HandIndexer:
    SUITS = 4
    RANKS = 13
    CARDS = 52
    MAX_GROUP_INDEX = 0x100000
    ROUND_SHIFT = 4
    ROUND_MASK = 0xf

    # TODO: This might not actually be good (to load from file) due to space reasons. 
    # Try computing it during the actual game and see if it runs in time.
    if all([exists(f) for f in ['nthUnset.npy', 'equal.npy', 'nCrRanks.npy', 'rankSetToIndex.npy', 'indexToRankSet.npy', 'suitPermutations.npy', 'nCrGroups.npy']]):
        nthUnset = np.load('nthUnset.npy', allow_pickle=True)
        equal = np.load('equal.npy', allow_pickle=True)
        nCrRanks = np.load('nCrRanks.npy', allow_pickle=True)
        rankSetToIndex = np.load('rankSetToIndex.npy', allow_pickle=True)
        indexToRankSet = np.load('indexToRankSet.npy', allow_pickle=True)
        suitPermutations = np.load('suitPermutations.npy', allow_pickle=True)
        nCrGroups = np.load('nCrGroups.npy', allow_pickle=True)
    else:
        nthUnset = np.zeros((1 << RANKS, RANKS), dtype=int)  # 2^13, 13
        equal = np.empty((1 << (SUITS - 1), SUITS), dtype=bool)  # 8, 3
        nCrRanks = np.zeros((RANKS + 1, RANKS + 1), dtype=int)  # 14, 14
        rankSetToIndex = np.zeros(1 << RANKS, dtype=int)  # 2^13
        indexToRankSet = np.zeros((RANKS + 1, 1 << RANKS), dtype=int)  # 14, 2^13
        nCrGroups = np.zeros((MAX_GROUP_INDEX, SUITS + 1), dtype=np.int64)

        for i in range(1 << (SUITS - 1)):
            for j in range(1, SUITS):
                equal[i, j] = (i & 1 << (j - 1)) != 0

        for i in range(1 << RANKS):
            set = ~i & (1 << RANKS) - 1
            for j in range(RANKS):
                nthUnset[i, j] = 0xff if set == 0 else number_of_trailing_zeros(set)
                set &= set - 1

        nCrRanks[0, 0] = 1
        for i in range(1, RANKS + 1):
            nCrRanks[i, 0] = nCrRanks[i, i] = 1
            for j in range(1, i):
                nCrRanks[i, j] = nCrRanks[i - 1, j - 1] + nCrRanks[i - 1, j]
        
        nCrGroups[0, 0] = 1
        for i in range(1, MAX_GROUP_INDEX):
            nCrGroups[i, 0] = 1
            if i < SUITS + 1:
                nCrGroups[i, i] = 1
            for j in range(1, min(SUITS + 1, i)):
                nCrGroups[i, j] = nCrGroups[i - 1, j - 1] + nCrGroups[i - 1, j]

        for i in range(1 << RANKS):
            set = i
            j = 1
            while set != 0:
                rankSetToIndex[i] += nCrRanks[number_of_trailing_zeros(set), j]
                j += 1
                set &= set - 1
            indexToRankSet[pop_count(i), rankSetToIndex[i]] = i 

        numPermutations = math.factorial(SUITS)

        suitPermutations = np.zeros((numPermutations, SUITS), dtype=int)
        for i in range(numPermutations):
            index = i
            used = 0
            for j in range(SUITS):
                suit = index % (SUITS - j)
                index //= SUITS - j
                shiftedSuit = nthUnset[used, suit]
                suitPermutations[i, j] = shiftedSuit
                used |= 1 << shiftedSuit

        np.save('nthUnset', nthUnset)
        np.save('equal', equal)
        np.save('nCrRanks', nCrRanks)
        np.save('rankSetToIndex', rankSetToIndex)
        np.save('indexToRankSet', indexToRankSet)
        np.save('suitPermutations', suitPermutations)
        np.save('nCrGroups', nCrGroups)


    def __init__(self, cardsPerRound):
        self.cardsPerRound = cardsPerRound
        self.rounds = len(cardsPerRound)

        self.permutationToConfiguration = [0] * self.rounds
        self.permutationToPi = [0] * self.rounds
        self.configurationToEqual = [0] * self.rounds
        self.configuration = [0] * self.rounds
        self.configurationToSuitSize = [0] * self.rounds
        self.configurationToOffset = [0] * self.rounds

        self.roundStart = [0] * self.rounds
        j = 0
        for i in range(self.rounds):
            self.roundStart[i] = j
            j += cardsPerRound[i]
        
        self.configurations = [0] * self.rounds
        self.enumerate_configurations(False)

        for i in range(self.rounds):
            self.configurationToEqual[i] = [0] * self.configurations[i]
            self.configurationToOffset[i] = [0] * self.configurations[i]
            self.configuration[i] = [0] * self.configurations[i]
            self.configurationToSuitSize[i] = [0] * self.configurations[i]
            for j in range(len(self.configuration[i])):
                self.configuration[i][j] = [0] * self.SUITS
                self.configurationToSuitSize[i][j] = [0] * self.SUITS
        
        self.configurations = [0] * self.rounds
        self.enumerate_configurations(True)

        self.roundSize = [0] * self.rounds
        for i in range(self.rounds):
            accum = 0
            for j in range(self.configurations[i]):
                next = accum + self.configurationToOffset[i][j]
                self.configurationToOffset[i][j] = accum
                accum = next
            self.roundSize[i] = accum

        self.permutations = [0] * self.rounds
        self.enumerate_permutations(False)

        for i in range(self.rounds):
            self.permutationToConfiguration[i] = [0] * self.permutations[i]
            self.permutationToPi[i] = [0] * self.permutations[i]

        self.enumerate_permutations(True)

    
    def create_public_flop_hands(self):
        print("Creating canonical samples of the 1755 public flop hand combinations...")

        publicFlopHandsFound = [False] * self.roundSize[0]
        self.publicFlopHands = [0] * self.roundSize[0]
        for i in range(self.roundSize[0]):
            self.publicFlopHands[i] = [0] * self.cardsPerRound[0]
        for card1 in range(52):
            for card2 in range(52):
                for card3 in range(52):
                    if card1 != card2 and card2 != card3 and card1 != card3:
                        index = self.index_last([card1, card2, card3])
                        if not publicFlopHandsFound[index]:
                            publicFlopHandsFound[index] = True
                            self.publicFlopHands[index] = [card1, card2, card3]
        
        print(self.publicFlopHands[:10])
        assert(sum(publicFlopHandsFound) == self.roundSize[0])


    def index_all(self, cards, indices):
        if self.rounds > 0:
            state = HandIndexerState()
            for i in range(self.rounds):
                indices[i] = self.index_next_round(state, cards)
            return indices[self.rounds - 1]
        return 0

    
    def index_last(self, cards):
        indices = [0] * self.rounds
        return self.index_all(cards, indices)

    
    def index_next_round(self, state, cards):
        round = state.round
        state.round += 1

        ranks = [0] * self.SUITS
        shiftedRanks = [0] * self.SUITS

        j = self.roundStart[round]
        for i in range(self.cardsPerRound[round]):
            rank = cards[j] >> 2
            suit = cards[j] & 3
            rankBit = 1 << rank
            ranks[suit] |= rankBit
            shiftedRanks[suit] |= rankBit >> pop_count((rankBit - 1) & state.usedRanks[suit])
            j += 1

        for i in range(self.SUITS):
            usedSize = pop_count(state.usedRanks[i])
            thisSize = pop_count(ranks[i])
            state.suitIndex[i] += state.suitMultiplier[i] * self.rankSetToIndex[shiftedRanks[i]]
            state.suitMultiplier[i] *= self.nCrRanks[self.RANKS - usedSize, thisSize]
            state.usedRanks[i] |= ranks[i]
        
        remaining = self.cardsPerRound[round]
        for i in range(self.SUITS - 1):
            thisSize = pop_count(ranks[i])
            state.permutationIndex += state.permutationMultiplier * thisSize
            state.permutationMultiplier *= remaining + 1
            remaining -= thisSize

        configuration = self.permutationToConfiguration[round][state.permutationIndex]
        piIndex = self.permutationToPi[round][state.permutationIndex]
        equalIndex = self.configurationToEqual[round][configuration]
        offset = self.configurationToOffset[round][configuration]
        pi = self.suitPermutations[piIndex]

        suitIndex = [0] * self.SUITS
        suitMultiplier = [0] * self.SUITS
        for i in range(self.SUITS):
            suitIndex[i] = state.suitIndex[pi[i]]
            suitMultiplier[i] = state.suitMultiplier[pi[i]]
        index = offset
        multiplier = 1
        i = 0
        while i < self.SUITS:
            if i + 1 < self.SUITS and self.equal[equalIndex, i + 1]:
                if i + 2 < self.SUITS and self.equal[equalIndex, i + 2]:
                    if i + 3 < self.SUITS and self.equal[equalIndex, i + 3]:
                        swap(suitIndex, i, i + 1)
                        swap(suitIndex, i + 2, i + 3)
                        swap(suitIndex, i, i + 2)
                        swap(suitIndex, i + 1, i + 3)
                        swap(suitIndex, i + 1, i + 2)
                        part = suitIndex[i] + self.nCrGroups[suitIndex[i + 1] + 1, 2] + self.nCrGroups[suitIndex[i + 2] + 2, 3] + self.nCrGroups[suitIndex[i + 3] + 3, 4]
                        size = self.nCrGroups[suitMultiplier[i] + 3, 4]
                        i += 4
                    else:
                        swap(suitIndex, i, i + 1)
                        swap(suitIndex, i, i + 2)
                        swap(suitIndex, i + 1, i + 2)
                        part = suitIndex[i] + self.nCrGroups[suitIndex[i + 1] + 1, 2] + self.nCrGroups[suitIndex[i + 2] + 2, 3]
                        size = self.nCrGroups[suitMultiplier[i] + 2, 3]
                        i += 3
                else:
                    swap(suitIndex, i, i + 1)
                    part = suitIndex[i] + self.nCrGroups[suitIndex[i + 1] + 1, 2]
                    size = self.nCrGroups[suitMultiplier[i] + 1, 2]
                    i += 2
            else:
                part = suitIndex[i]
                size = suitMultiplier[i]
                i += 1
        
            index += multiplier * part
            multiplier *= size
        
        return index


    def unindex(self, round, index, cards):
        if round >= self.rounds or index >= self.roundSize[round]:
            return False
        
        low = 0
        high = self.configurations[round]
        configurationIdx = 0

        while c_uint(low).value < c_uint(high).value:
            mid = (low + high) // 2
            if self.configurationToOffset[round][mid] <= index:
                configurationIdx = mid
                low = mid + 1
            else:
                high = mid
        index -= self.configurationToOffset[round][configurationIdx]

        suitIndex = [0] * self.SUITS
        i = 0
        while i < self.SUITS:
            j = i + 1
            while j < self.SUITS and self.configuration[round][configurationIdx][j] == self.configuration[round][configurationIdx][i]:
                j += 1
            
            suitSize = self.configurationToSuitSize[round][configurationIdx][i]
            groupSize = self.nCrGroups[suitSize + j - i - 1, j - i]

            groupIndex = c_long(c_ulong(index).value % c_ulong(groupSize).value).value
            index = c_long(c_ulong(index).value // c_ulong(groupSize).value).value

            while i < j - 1:
                if groupIndex == 0:
                    suitIndex[i] = math.floor(- j - i)
                    low = math.floor(- j - i)
                    high = math.ceil(- j + i + 1)
                else:
                    suitIndex[i] = math.floor(math.exp(math.log(groupIndex) / (j - i) - 1 + math.log(j - i)) - j - i)
                    low = math.floor(math.exp(math.log(groupIndex) / (j - i) - 1 + math.log(j - i)) - j - i)
                    high = math.ceil(math.exp(math.log(groupIndex) / (j - i) + math.log(j - i)) - j + i + 1)
                if c_uint(high).value > c_uint(suitSize).value:
                    high = suitSize
                if c_uint(high).value <= c_uint(low).value:
                    low = 0
                while c_uint(low).value < c_uint(high).value:
                    mid = c_int(c_uint(low + high).value // 2).value
                    if self.nCrGroups[mid + j - i - 1, j - i] <= groupIndex:
                        suitIndex[i] = mid
                        low = mid + 1
                    else:
                        high = mid
                groupIndex -= self.nCrGroups[suitIndex[i] + j - i - 1, j - i]
                i += 1
            
            suitIndex[i] = groupIndex
            i += 1

        location = self.roundStart.copy()
        for i in range(self.SUITS):
            used = 0
            m = 0
            for j in range(self.rounds):
                n = self.configuration[round][configurationIdx][i] >> (self.ROUND_SHIFT * (self.rounds - j - 1)) & self.ROUND_MASK
                roundSize = self.nCrRanks[self.RANKS - m, n]
                m += n
                roundIdx = c_int(c_ulong(suitIndex[i]).value % c_ulong(roundSize).value).value
                suitIndex[i] = c_long(c_ulong(suitIndex[i]).value // c_ulong(roundSize).value).value
                shiftedCards = self.indexToRankSet[n, roundIdx]
                rankSet = 0
                for k in range(n):
                    shiftedCard = shiftedCards & -shiftedCards
                    shiftedCards ^= shiftedCard
                    card = self.nthUnset[used, number_of_trailing_zeros(shiftedCard)]
                    rankSet |= 1 << card
                    cards[location[j]] = card << 2 | i
                    location[j] += 1
                used |= rankSet

        return True


    def enumerate_configurations(self, tabulate):
        used = [0] * self.SUITS
        configuration = [0] * self.SUITS
        self.enumerate_configurations_r(0, self.cardsPerRound[0], 0, (1 << self.SUITS) - 2, used, configuration, tabulate)


    def enumerate_configurations_r(self, round, remaining, suit, equal, used, configuration, tabulate):
        if suit == self.SUITS:
            if tabulate:
                self.tabulate_configurations(round, configuration)
            else:
                self.configurations[round] += 1
            
            if round + 1 < self.rounds:
                self.enumerate_configurations_r(round + 1, self.cardsPerRound[round + 1], 0, equal, used, configuration, tabulate)
        else:
            min = 0
            if suit == self.SUITS - 1:
                min = remaining
            
            max = self.RANKS - used[suit]
            if remaining < max:
                max = remaining
            
            previous = self.RANKS + 1
            wasEqual = (equal & 1 << suit) != 0
            if wasEqual:
                previous = configuration[suit - 1] >> (self.ROUND_SHIFT * (self.rounds - round - 1)) & self.ROUND_MASK
                if previous < max:
                    max = previous

            oldConfiguration = configuration[suit]
            oldUsed = used[suit]
            for i in range(min, max + 1):
                newConfiguration = oldConfiguration | i << (self.ROUND_SHIFT * (self.rounds - round - 1))
                newEqual = ((equal & ~(1 << suit)) | (wasEqual & (1 if i == previous else 0)) << suit)
                
                used[suit] = oldUsed + i
                configuration[suit] = newConfiguration
                self.enumerate_configurations_r(round, remaining - i, suit + 1, newEqual, used, configuration, tabulate)
                configuration[suit] = oldConfiguration
                used[suit] = oldUsed

    
    def tabulate_configurations(self, round, configuration):
        id = self.configurations[round]
        self.configurations[round] += 1

        try: 
            while id > 0:
                for i in range(self.SUITS):
                    if configuration[i] < self.configuration[round][id - 1][i]:
                        break
                    elif configuration[i] > self.configuration[round][id - 1][i]:
                        raise GetOutOfLoop
                for i in range(self.SUITS):
                    self.configuration[round][id][i] = self.configuration[round][id - 1][i]
                    self.configurationToSuitSize[round][id][i] = self.configurationToSuitSize[round][id - 1][i]
                self.configurationToOffset[round][id] = self.configurationToOffset[round][id - 1]
                self.configurationToEqual[round][id] = self.configurationToEqual[round][id - 1]
                id -= 1
        except GetOutOfLoop:
            pass

        self.configurationToOffset[round][id] = 1
        self.configuration[round][id] = configuration.copy()

        equal = 0
        i = 0
        while i < self.SUITS:
            size = 1
            remaining = self.RANKS
            j = 0
            while j <= round:
                ranks = configuration[i] >> (self.ROUND_SHIFT * (self.rounds - j - 1)) & self.ROUND_MASK
                size *= self.nCrRanks[remaining, ranks]
                remaining -= ranks
                j += 1

            j = i + 1
            while j < self.SUITS and configuration[j] == configuration[i]:
                j += 1
            
            for k in range(i, j):
                self.configurationToSuitSize[round][id][k] = size
            
            self.configurationToOffset[round][id] *= self.nCrGroups[size + j - i - 1, j - i]

            for k in range(i + 1, j):
                equal |= 1 << k
            
            i = j
        
        self.configurationToEqual[round][id] = equal >> 1


    def enumerate_permutations(self, tabulate):
        used = [0] * self.SUITS
        count = [0] * self.SUITS

        self.enumerate_permutations_r(0, self.cardsPerRound[0], 0, used, count, tabulate)

    
    def enumerate_permutations_r(self, round, remaining, suit, used, count, tabulate):
        if suit == self.SUITS:
            if tabulate:
                self.tabulate_permutations(round, count)
            else:
                self.count_permutations(round, count)

            if round + 1 < self.rounds:
                self.enumerate_permutations_r(round + 1, self.cardsPerRound[round + 1], 0, used, count, tabulate)
        else:
            min = 0
            if suit == self.SUITS - 1:
                min = remaining
            
            max = self.RANKS - used[suit]
            if remaining < max:
                max = remaining
            
            oldCount = count[suit]
            oldUsed = used[suit]
            for i in range(min, max + 1):
                newCount = oldCount | i << (self.ROUND_SHIFT * (self.rounds - round - 1))
                
                used[suit] = oldUsed + i
                count[suit] = newCount
                self.enumerate_permutations_r(round, remaining - i, suit + 1, used, count, tabulate)
                count[suit] = oldCount
                used[suit] = oldUsed
            
    
    def count_permutations(self, round, count):
        idx = 0
        mult = 1
        for i in range(round + 1):
            remaining = self.cardsPerRound[i]
            for j in range(self.SUITS - 1):
                size = count[j] >> ((self.rounds - i - 1) * self.ROUND_SHIFT) & self.ROUND_MASK
                idx += mult * size
                mult *= remaining + 1
                remaining -= size
        
        if self.permutations[round] < idx + 1:
            self.permutations[round] = idx + 1

    
    def tabulate_permutations(self, round, count):
        idx = 0
        mult = 1
        for i in range(round + 1):
            remaining = self.cardsPerRound[i]
            for j in range(self.SUITS - 1):
                size = count[j] >> ((self.rounds - i - 1) * self.ROUND_SHIFT) & self.ROUND_MASK
                idx += mult * size
                mult *= remaining + 1
                remaining -= size

        pi = [0] * self.SUITS
        for i in range(self.SUITS):
            pi[i] = i
        
        for i in range(1, self.SUITS):
            j = i
            pi_i = pi[i]
            while j > 0:
                if count[pi_i] > count[pi[j - 1]]:
                    pi[j] = pi[j - 1]
                else:
                    break
                j -= 1
            pi[j] = pi_i
        
        pi_idx = 0
        pi_mult = 1
        pi_used = 0
        for i in range(self.SUITS):
            this_bit = 1 << pi[i]
            smaller = pop_count((this_bit - 1) & pi_used)
            pi_idx += (pi[i] - smaller) * pi_mult
            pi_mult *= self.SUITS - i
            pi_used |= this_bit

        self.permutationToPi[round][idx] = pi_idx

        low = 0
        high = self.configurations[round]
        while low < high:
            mid = (low + high) // 2
            compare = 0
            for i in range(self.SUITS):
                that = count[pi[i]]
                other = self.configuration[round][mid][i]
                if other > that:
                    compare = -1
                    break
                elif other < that:
                    compare = 1
                    break
            if compare == -1:
                high = mid
            elif compare == 0:
                low = high = mid
            else:
                low = mid + 1

        self.permutationToConfiguration[round][idx] = low