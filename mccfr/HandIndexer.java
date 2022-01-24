package mccfr;

import java.util.Arrays;
import java.lang.Integer;
import java.math.BigInteger;

class HandIndexerState {
    public int[] suitIndex = new int[HandIndexer.SUITS];
    public int[] suitMultiplier = new int[HandIndexer.SUITS];
    public int round, permutationIndex, permutationMultiplier;
    public int[] usedRanks = new int[HandIndexer.SUITS];

    public HandIndexerState() {
        permutationMultiplier = 1;
        for (int i = 0; i < HandIndexer.SUITS; ++i)
            suitMultiplier[i] = 1;
    }
}

public class HandIndexer {
    public static int SUITS = 4;
    public static int RANKS = 13;
    public static int CARDS = 52;
    private static int MAX_GROUP_INDEX = 0x100000;
    private static int ROUND_SHIFT = 4;
    private static int ROUND_MASK = 0xf;

    private static int[][] nthUnset = new int[1 << RANKS][RANKS];
    private static boolean[][] equal = new boolean[1 << (SUITS - 1)][SUITS];
    private static int[][] nCrRanks = new int[RANKS + 1][RANKS + 1];
    private static int[] rankSetToIndex = new int[1 << RANKS];
    private static int[][] indexToRankSet = new int[RANKS + 1][1 << RANKS];
    private static int[][] suitPermutations;
    private static long[][] nCrGroups = new long[MAX_GROUP_INDEX][SUITS + 1];

    public int rounds;
    public int[] cardsPerRound;
    public int[] configurations;
    public int[] permutations;
    public long[] roundSize;
    private int[] roundStart;
    private int[][] permutationToConfiguration;
    private int[][] permutationToPi;
    private int[][] configurationToEqual;
    private int[][][] configuration;
    private int[][][] configurationToSuitSize;
    private long[][] configurationToOffset;

    private int[][] publicFlopHands;

    static {
        for (int i = 0; i < 1 << (SUITS - 1); ++i)
            for (int j = 1; j < SUITS; j++)
                equal[i][j] = (i & 1 << (j - 1)) != 0;

        for (int i = 0; i < 1 << RANKS; ++i)
            for (int j = 0, set = ~i & (1 << RANKS) - 1; j < RANKS; ++j, set &= set - 1)
                nthUnset[i][j] = set == 0 ? 0xff : numberOfTrailingZeros(set);

        nCrRanks[0][0] = 1;
        for (int i = 1; i < RANKS + 1; ++i) {
            nCrRanks[i][0] = nCrRanks[i][i] = 1;
            for (int j = 1; j < i; ++j) {
                nCrRanks[i][j] = nCrRanks[i - 1][j - 1] + nCrRanks[i - 1][j];
            }
        }

        nCrGroups[0][0] = 1;
        for (int i = 1; i < MAX_GROUP_INDEX; ++i) {
            nCrGroups[i][0] = 1;
            if (i < SUITS + 1)
                nCrGroups[i][i] = 1;
            for (int j = 1; j < (i < (SUITS + 1) ? i : (SUITS + 1)); ++j)
                nCrGroups[i][j] = nCrGroups[i - 1][j - 1] + nCrGroups[i - 1][j];
        }

        for (int i = 0; i < 1 << RANKS; ++i) {
            for (int set = i, j = 1; set != 0; ++j, set &= set - 1)
                rankSetToIndex[i] += nCrRanks[numberOfTrailingZeros(set)][j];
            indexToRankSet[Integer.bitCount(i)][rankSetToIndex[i]] = i;
        }

        int numPermutations = 1;
        for (int i = 2; i <= SUITS; ++i)
            numPermutations *= i;

        suitPermutations = new int[numPermutations][];
        for (int i = 0; i < numPermutations; ++i) {
            suitPermutations[i] = new int[SUITS];
            for (int j = 0, index = i, used = 0; j < SUITS; ++j) {
                int suit = index % (SUITS - j);
                index /= SUITS - j;
                int shiftedSuit = nthUnset[used][suit];
                suitPermutations[i][j] = shiftedSuit;
                used |= 1 << shiftedSuit;
            }
        }
    }

    public HandIndexer(int[] cardsPerRound) {
        this.cardsPerRound = cardsPerRound;
        rounds = cardsPerRound.length;

        permutationToConfiguration = new int[rounds][];
        permutationToPi = new int[rounds][];
        configurationToEqual = new int[rounds][];
        configuration = new int[rounds][][];
        configurationToSuitSize = new int[rounds][][];
        configurationToOffset = new long[rounds][];

        roundStart = new int[rounds];
        for (int i = 0, j = 0; i < rounds; ++i) {
            roundStart[i] = j;
            j += cardsPerRound[i];
        }

        configurations = new int[rounds];
        enumerateConfigurations(false);

        for (int i = 0; i < rounds; ++i) {
            configurationToEqual[i] = new int[configurations[i]];
            configurationToOffset[i] = new long[configurations[i]];
            configuration[i] = new int[configurations[i]][];
            configurationToSuitSize[i] = new int[configurations[i]][];
            for(int j = 0; j < configuration[i].length; ++j) {
                configuration[i][j] = new int[SUITS];
                configurationToSuitSize[i][j] = new int[SUITS];
            }
        }

        configurations = new int[rounds];
        enumerateConfigurations(true);

        roundSize = new long[rounds];
        for (int i = 0; i < rounds; ++i) {
            long accum = 0;
            for (int j = 0; j < configurations[i]; ++j) {
                long next = accum + configurationToOffset[i][j];
                configurationToOffset[i][j] = accum;
                accum = next;
            }
            roundSize[i] = accum;
        }

        permutations = new int[rounds];
        enumeratePermutations(false);

        for (int i = 0; i < rounds; ++i) {
            permutationToConfiguration[i] = new int[permutations[i]];
            permutationToPi[i] = new int[permutations[i]];
        }

        enumeratePermutations(true);
    }

    public void createPublicFlopHands()
    {
        System.out.println("Creating 1755 canonical flops...");

        boolean[] publicFlopHandsFound = new boolean[(int)roundSize[0]];
        publicFlopHands = new int[(int)roundSize[0]][];
        for (int i = 0; i < roundSize[0]; ++i)
            publicFlopHands[i] = new int[cardsPerRound[0]];
        for (int card1 = 0; card1 < 52; card1++) {
            for (int card2 = 0; card2 < 52; card2++) {
                for (int card3 = 0; card3 < 52; card3++) {
                    if (card1 != card2 && card2 != card3 && card1 != card3) {
                        int index = (int)(indexLast(new int[] { card1, card2, card3 }));
                        if (!publicFlopHandsFound[index]) {
                            publicFlopHandsFound[index] = true;
                            publicFlopHands[index] = new int[] { card1, card2, card3 };
                        }
                    }
                }
            }
        }
        int count = 0;
        for (Boolean b : publicFlopHandsFound) if (b) count++;
        assert(count == roundSize[0]);
        for (int[] el : Arrays.copyOfRange(publicFlopHands, 0, 10))
            System.out.println(Arrays.toString(el));
    }

    public long indexAll(int[] cards, long[] indices) {
        if (rounds > 0) {
            HandIndexerState state = new HandIndexerState();
            for (int i = 0; i < rounds; i++)
                indices[i] = indexNextRound(state, cards);
            return indices[rounds - 1];
        }
        return 0;
    }

    public long indexLast(int[] cards) {
        long[] indices = new long[rounds];
        return indexAll(cards, indices);
    }

    public long indexNextRound(HandIndexerState state, int[] cards) {
        int round = state.round++;

        int[] ranks = new int[SUITS];
        int[] shiftedRanks = new int[SUITS];

        for (int i = 0, j = roundStart[round]; i < cardsPerRound[round]; ++i, ++j) {
            int rank = cards[j] >> 2, suit = cards[j] & 3, rankBit = 1 << rank;
            ranks[suit] |= rankBit;
            shiftedRanks[suit] |= (rankBit >> Integer.bitCount((rankBit - 1) & state.usedRanks[suit]));
        }

        for (int i = 0; i < SUITS; ++i) {
            int usedSize = Integer.bitCount(state.usedRanks[i]), thisSize = Integer.bitCount(ranks[i]);
            state.suitIndex[i] += state.suitMultiplier[i] * rankSetToIndex[shiftedRanks[i]];
            state.suitMultiplier[i] *= nCrRanks[RANKS - usedSize][thisSize];
            state.usedRanks[i] |= ranks[i];
        }

        for (int i = 0, remaining = cardsPerRound[round]; i < SUITS - 1; ++i) {
            int thisSize = Integer.bitCount(ranks[i]);
            state.permutationIndex += state.permutationMultiplier * thisSize;
            state.permutationMultiplier *= remaining + 1;
            remaining -= thisSize;
        }

        int configuration = permutationToConfiguration[round][state.permutationIndex];
        int piIndex = permutationToPi[round][state.permutationIndex];
        int equalIndex = configurationToEqual[round][configuration];
        long offset = configurationToOffset[round][configuration];
        int[] pi = suitPermutations[piIndex];

        int[] suitIndex = new int[SUITS], suitMultiplier = new int[SUITS];
        for (int i = 0; i < SUITS; ++i) {
            suitIndex[i] = state.suitIndex[pi[i]];
            suitMultiplier[i] = state.suitMultiplier[pi[i]];
        }
        long index = offset, multiplier = 1;
        for (int i = 0; i < SUITS;) {
            long part, size;

            if (i + 1 < SUITS && equal[equalIndex][i + 1]) {
                if (i + 2 < SUITS && equal[equalIndex][i + 2]) {
                    if (i + 3 < SUITS && equal[equalIndex][i + 3]) {
                        swap(suitIndex, i, i + 1);
                        swap(suitIndex, i + 2, i + 3);
                        swap(suitIndex, i, i + 2);
                        swap(suitIndex, i + 1, i + 3);
                        swap(suitIndex, i + 1, i + 2);
                        part = suitIndex[i]
                            + nCrGroups[suitIndex[i + 1] + 1][2]
                            + nCrGroups[suitIndex[i + 2] + 2][3]
                            + nCrGroups[suitIndex[i + 3] + 3][4];
                        size = nCrGroups[suitMultiplier[i] + 3][4];
                        i += 4;
                    }
                    else {
                        swap(suitIndex, i, i + 1);
                        swap(suitIndex, i, i + 2);
                        swap(suitIndex, i + 1, i + 2);
                        part = suitIndex[i] + nCrGroups[suitIndex[i + 1] + 1][2]
                            + nCrGroups[suitIndex[i + 2] + 2][3];
                        size = nCrGroups[suitMultiplier[i] + 2][3];
                        i += 3;
                    }
                }
                else {
                    swap(suitIndex, i, i + 1);
                    part = suitIndex[i] + nCrGroups[suitIndex[i + 1] + 1][2];
                    size = nCrGroups[suitMultiplier[i] + 1][2];
                    i += 2;
                }
            }
            else {
                part = suitIndex[i];
                size = suitMultiplier[i];
                i += 1;
            }

            index += multiplier * part;
            multiplier *= size;
        }
        return index;
    }

    public boolean unindex(int round, long index, int[] cards) {
        if (round >= rounds || index >= roundSize[round])
            return false;

        int low = 0, high = configurations[round];
        int configurationIdx = 0;

        while (Integer.compareUnsigned(low, high) < 0) {
            int mid = ((low + high) / 2);
            if (configurationToOffset[round][mid] <= index) {
                configurationIdx = mid;
                low = mid + 1;
            }
            else {
                high = mid;
            }
        }
        index -= configurationToOffset[round][configurationIdx];

        long[] suitIndex = new long[SUITS];
        for (int i = 0; i < SUITS;)
        {
            int j = i + 1;
            while (j < SUITS && configuration[round][configurationIdx][j] ==
                configuration[round][configurationIdx][i])
            {
                ++j;
            }

            int suitSize = configurationToSuitSize[round][configurationIdx][i];
            long groupSize = nCrGroups[suitSize + j - i - 1][j - i];

            long groupIndex = Long.remainderUnsigned(index, groupSize);

            index = Long.divideUnsigned(index, groupSize);

            for (; i < j - 1; ++i) {
                suitIndex[i] = (int)Math.floor(Math.exp(Math.log(groupIndex) / (j - i) - 1 + Math.log(j - i)) - j - i);
                low = (int)Math.floor(Math.exp(Math.log(groupIndex) / (j - i) - 1 + Math.log(j - i)) - j - i);
                high = (int)Math.ceil(Math.exp(Math.log(groupIndex) / (j - i) + Math.log(j - i)) - j + i+ 1);
                if (Integer.compareUnsigned(high, suitSize) > 0)
                    high = suitSize;
                if (Integer.compareUnsigned(high, low) <= 0)
                    low = 0;
                while (Integer.compareUnsigned(low, high) < 0) {
                    int mid = (int)(toUint(low + high)/2);
                    if (nCrGroups[mid + j - i - 1][j - i] <= groupIndex) {
                        suitIndex[i] = mid;
                        low = mid + 1;
                    }
                    else {
                        high = mid;
                    }
                }
                groupIndex -= nCrGroups[(int)(suitIndex[i] + j - i - 1)][j - i];
            }

            suitIndex[i] = groupIndex;
            ++i;
        }

        int[] location = roundStart.clone();
        for (int i = 0; i < SUITS; ++i) {
            int used = 0, m = 0;
            for (int j = 0; j < rounds; ++j) {
                int n = configuration[round][configurationIdx][i] >> (ROUND_SHIFT * (rounds - j - 1)) & ROUND_MASK;
                int roundSize = nCrRanks[RANKS - m][n];
                m += n;
                int roundIdx = (int)(Long.remainderUnsigned(suitIndex[i], roundSize));
                suitIndex[i] = Long.divideUnsigned(suitIndex[i], roundSize);
                int shiftedCards = indexToRankSet[n][roundIdx], rankSet = 0;
                for (int k = 0; k < n; ++k) {
                    int shiftedCard = shiftedCards & -shiftedCards;
                    shiftedCards ^= shiftedCard;
                    int card = nthUnset[used][numberOfTrailingZeros(shiftedCard)];
                    rankSet |= (1 << card);
                    cards[location[j]++] = card << 2 | i;
                }
                used |= rankSet;
            }
        }
        return true;
    }

    private void swap(int[] suitIndex, int u, int v) {
        if (suitIndex[u] > suitIndex[v]) {
            int tmp = suitIndex[u];
            suitIndex[u] = suitIndex[v];
            suitIndex[v] = tmp;
        }
    }

    private void enumerateConfigurations(boolean tabulate) {
        int[] used = new int[SUITS];
        int[] configuration = new int[SUITS];

        enumerateConfigurationsR(0, cardsPerRound[0], 0, ((1 << SUITS) - 2), used, configuration, tabulate);
    }

    private void enumerateConfigurationsR(int round, int remaining, int suit, int equal, int[] used, int[] configuration, boolean tabulate)
    {
        if (suit == SUITS) {
            if (tabulate)
                tabulateConfigurations(round, configuration);
            else
                ++configurations[round];

            if (round + 1 < rounds)
                enumerateConfigurationsR(round + 1, cardsPerRound[round + 1], 0, equal, used, configuration, tabulate);
        }
        else {
            int min = 0;
            if (suit == SUITS - 1)
                min = remaining;

            int max = RANKS - used[suit];
            if (remaining < max)
                max = remaining;

            int previous = RANKS + 1;
            boolean wasEqual = (equal & 1 << suit) != 0;
            if (wasEqual) {
                previous = configuration[suit - 1] >> (ROUND_SHIFT * (rounds - round - 1)) & ROUND_MASK;
                if (previous < max)
                    max = previous;
            }

            int oldConfiguration = configuration[suit], oldUsed = used[suit];
            for (int i = min; i <= max; ++i) {
                int newConfiguration = oldConfiguration | i << (ROUND_SHIFT * (rounds - round - 1));
                int newEqual = ((equal & ~(1 << suit)) | (wasEqual & (i == previous) ? 1 : 0) << suit);

                used[suit] = oldUsed + i;
                configuration[suit] = newConfiguration;
                enumerateConfigurationsR(round, remaining - i, suit + 1, newEqual, used, configuration,
                    tabulate);
                configuration[suit] = oldConfiguration;
                used[suit] = oldUsed;
            }
        }
    }

    private void tabulateConfigurations(int round, int[] configuration)
    {
        int id = configurations[round]++;

        OUT:
        for (; id > 0; --id) {
            for (int i = 0; i < SUITS; ++i) {
                if (configuration[i] < this.configuration[round][id - 1][i])
                    break;
                else if (configuration[i] > this.configuration[round][id - 1][i])
                    break OUT;
            }
            for (int i = 0; i < SUITS; ++i) {
                this.configuration[round][id][i] = this.configuration[round][id - 1][i];
                configurationToSuitSize[round][id][i] = configurationToSuitSize[round][id - 1][i];
            }
            configurationToOffset[round][id] = configurationToOffset[round][id - 1];
            configurationToEqual[round][id] = configurationToEqual[round][id - 1];
        }

        configurationToOffset[round][id] = 1;
        this.configuration[round][id] = configuration.clone();

        int equal = 0;
        for (int i = 0; i < SUITS;) {
            int size = 1;
            int j = 0;
            for (int remaining = RANKS; j <= round; ++j) {
                int ranks = configuration[i] >> (ROUND_SHIFT * (rounds - j - 1)) & ROUND_MASK;
                size *= nCrRanks[remaining][ranks];
                remaining -= ranks;
            }

            j = i + 1;
            while (j < SUITS && configuration[j] == configuration[i])
                ++j;

            for (int k = i; k < j; ++k)
                configurationToSuitSize[round][id][k] = size;

            configurationToOffset[round][id] *= nCrGroups[size + j - i - 1][j - i];

            for (int k = i + 1; k < j; ++k)
                equal |= 1 << k;

            i = j;
        }

        configurationToEqual[round][id] = equal >> 1;
    }

    private void enumeratePermutations(boolean tabulate) {
        int[] used = new int[SUITS];
        int[] count = new int[SUITS];

        enumeratePermutationsR(0, cardsPerRound[0], 0, used, count, tabulate);
    }

    private void enumeratePermutationsR(int round, int remaining, int suit, int[] used, int[] count, boolean tabulate)
    {
        if (suit == SUITS) {
            if (tabulate)
                tabulatePermutations(round, count);
            else
                countPermutations(round, count);

            if (round + 1 < rounds)
                enumeratePermutationsR(round + 1, cardsPerRound[round + 1], 0, used, count, tabulate);
        }
        else {
            int min = 0;
            if (suit == SUITS - 1)
                min = remaining;

            int max = RANKS - used[suit];
            if (remaining < max)
                max = remaining;

            int oldCount = count[suit], oldUsed = used[suit];
            for (int i = min; i <= max; ++i)
            {
                int newCount = oldCount | i << (ROUND_SHIFT * (rounds - round - 1));

                used[suit] = oldUsed + i;
                count[suit] = newCount;
                enumeratePermutationsR(round, remaining - i, suit + 1, used, count, tabulate);
                count[suit] = oldCount;
                used[suit] = oldUsed;
            }
        }
    }

    private void countPermutations(int round, int[] count) {
        int idx = 0, mult = 1;
        for (int i = 0; i <= round; ++i) {
            for (int j = 0, remaining = cardsPerRound[i]; j < SUITS - 1; ++j) {
                int size = count[j] >> ((rounds - i - 1) * ROUND_SHIFT) & ROUND_MASK;
                idx += mult * size;
                mult *= remaining + 1;
                remaining -= size;
            }
        }

        if (permutations[round] < idx + 1)
            permutations[round] = idx + 1;
    }

    private void tabulatePermutations(int round, int[] count) {
        int idx = 0, mult = 1;
        for (int i = 0; i <= round; ++i) {
            for (int j = 0, remaining = cardsPerRound[i]; j < SUITS - 1; ++j) {
                int size = count[j] >> ((rounds - i - 1) * ROUND_SHIFT) & ROUND_MASK;
                idx += mult * size;
                mult *= remaining + 1;
                remaining -= size;
            }
        }

        int[] pi = new int[SUITS];
        for (int i = 0; i < SUITS; ++i)
            pi[i] = i;

        for (int i = 1; i < SUITS; ++i) {
            int j = i, pi_i = pi[i];
            for (; j > 0; --j) {
                if (count[pi_i] > count[pi[j - 1]])
                    pi[j] = pi[j - 1];
                else
                    break;
            }
            pi[j] = pi_i;
        }

        int pi_idx = 0, pi_mult = 1, pi_used = 0;
        for (int i = 0; i < SUITS; ++i) {
            int this_bit = (1 << pi[i]);
            int smaller = Integer.bitCount((this_bit - 1) & pi_used);
            pi_idx += (pi[i] - smaller) * pi_mult;
            pi_mult *= SUITS - i;
            pi_used |= this_bit;
        }

        permutationToPi[round][idx] = pi_idx;

        int low = 0, high = configurations[round];
        while (low < high) {
            int mid = (low + high) / 2;

            int compare = 0;
            for (int i = 0; i < SUITS; ++i) {
                int that = count[pi[i]];
                int other = configuration[round][mid][i];
                if (other > that) {
                    compare = -1;
                    break;
                }
                else if (other < that) {
                    compare = 1;
                    break;
                }
            }

            if (compare == -1)
                high = mid;
            else if (compare == 0)
                low = high = mid;
            else
                low = mid + 1;
        }

        permutationToConfiguration[round][idx] = low;
    }

    public static int numberOfTrailingZeros(int n) {
        int mask = 1;
        for (int i = 0; i < 32; i++, mask <<= 1)
            if ((n & mask) != 0)
                return i;
        return 32;
    }

    public static long toUint(int n) {
        return n & 0xffffffffL;
    }

    // private static final BigInteger TWO_64 = BigInteger.ONE.shiftLeft(64);

    // public static long toUlong(long l) {
    //     BigInteger b = BigInteger.valueOf(l);
    //     if (b.signum() < 0)
    //         b = b.add(TWO_64);
    //     return b.longValue();
    // }
}