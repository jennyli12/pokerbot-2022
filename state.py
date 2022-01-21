from collections import namedtuple
import eval7
import numpy as np
import random

from tables.hand_indexer import HandIndexer


indexer_2 = HandIndexer([2])
indexer_2_3 = HandIndexer([2, 3])
indexer_2_4 = HandIndexer([2, 4])
indexer_2_5 = HandIndexer([2, 5])

flop_clusters = np.load('tables/flop_clusters.npy')
turn_clusters = np.load('tables/turn_clusters.npy')
river_clusters = np.load('tables/river_clusters.npy')

STARTING_STACK = 200
BIG_BLIND = 2
SMALL_BLIND = 1

RAISES = [0.75, 1.5, 3]  # percentage of pot for raise
RAISE_LETTER = ['x', 'y', 'z']
RAISE_LETTER_INV = {'x': 0, 'y': 1, 'z': 2}
RAISE_SET = {'x', 'y', 'z'}

RANK = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
SUIT = {'s': 0, 'h': 1, 'd': 2, 'c': 3}
RANK_INV = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']


def get_root_state_parallel(traverser, possible_hands):
    hand_str = random.choice(possible_hands)
    rank1, rank2 = hand_str[0], hand_str[1]
    suit1 = 's'
    if len(hand_str) == 2 or hand_str[-1] == 'o':
        suit2 = 'h'
    else:
        suit2 = 's'
    traverser_hand = [eval7.Card(rank1 + suit1), eval7.Card(rank2 + suit2)]
    deck = eval7.Deck()
    deck.cards = [card for card in deck.cards if card not in set(traverser_hand)]
    deck.shuffle()
    other_hand = deck.deal(2)
    if traverser == 0:
        hands = [traverser_hand, other_hand]
    else:
        hands = [other_hand, traverser_hand]
    deck = ([], deck)
    pips = [SMALL_BLIND, BIG_BLIND]
    stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND]
    return RoundState(0, 0, pips, stacks, hands, deck, "")

def get_root_state():
    deck = eval7.Deck()
    deck.shuffle()
    deck = ([], deck)
    hands = [deck[1].deal(2), deck[1].deal(2)]
    pips = [SMALL_BLIND, BIG_BLIND]
    stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND]
    return RoundState(0, 0, pips, stacks, hands, deck, "")

def get_first_action_states():
    states = []
    for i in range(169):
        rank1 = RANK_INV[i // 13]
        rank2 = RANK_INV[i % 13]
        suit1 = 's'
        if i % 13 > i // 13:
            suit2 = 's'
        else:
            suit2 = 'h'
        sb_hand = [eval7.Card(rank1 + suit1), eval7.Card(rank2 + suit2)]

        deck = eval7.Deck()
        deck.cards = [card for card in deck.cards if card not in set(sb_hand)]
        deck.shuffle()
        bb_hand = deck.deal(2)
        hands = [sb_hand, bb_hand]
        deck = ([], deck)
        pips = [SMALL_BLIND, BIG_BLIND]
        stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND]
        states.append(RoundState(0, 0, pips, stacks, hands, deck, ""))
    return states

TerminalState = namedtuple('TerminalState', ['deltas'])

class RoundState(namedtuple('_RoundState', ['button', 'street', 'pips', 'stacks', 'hands', 'deck', 'history'])):
    '''
    Encodes the game tree for one round of poker.
    '''
    def get_card_index(self, card):
        rank = RANK[card[0]]
        suit = SUIT[card[1]]
        return rank * 4 + suit

    def get_infoset_str(self):
        active = self.button % 2
        cards = self.hands[active] + self.deck[0]
        card_array = [self.get_card_index(str(card)) for card in cards]
        if self.street == 0:
            card_str = 'P' + str(indexer_2.index_last(card_array))
        elif self.street == 3:
            card_str = 'F' + str(flop_clusters[indexer_2_3.index_last(card_array)])
        elif self.street == 4:
            card_str = 'T' + str(turn_clusters[indexer_2_4.index_last(card_array)])
        else:
            card_str = 'R' + str(river_clusters[indexer_2_5.index_last(card_array)])
        return self.history + card_str

    def showdown(self):
        '''
        Compares the players' hands and computes payoffs.
        '''
        score0 = eval7.evaluate(self.deck[0] + self.hands[0])
        score1 = eval7.evaluate(self.deck[0] + self.hands[1])
        if score0 > score1:
            delta = STARTING_STACK - self.stacks[1]
        elif score0 < score1:
            delta = self.stacks[0] - STARTING_STACK
        else:  # split the pot
            delta = (self.stacks[0] - self.stacks[1]) // 2
        return TerminalState([delta, -delta])

    def get_actions(self):
        active = self.button % 2
        continue_cost = self.pips[1-active] - self.pips[active]

        raise_actions = []
        too_many_raises = len(self.history) >= 5 and self.history[-1] in RAISE_SET and self.history[-2] in RAISE_SET and \
            self.history[-3] in RAISE_SET and self.history[-4] in RAISE_SET and self.history[-5] in RAISE_SET
        if not too_many_raises:
            min_raise, max_raise = self.raise_bounds()
            for i in range(len(RAISES)):
                pot = 2 * STARTING_STACK - (self.stacks[0] + self.stacks[1])
                raise_amount = int(RAISES[i] * (pot + continue_cost)) + continue_cost + self.pips[active]
                if raise_amount >= min_raise and raise_amount < max_raise:
                    raise_actions.append(RAISE_LETTER[i])
            raise_actions.append('a')  # all in

        if continue_cost == 0:
            # we can only raise the stakes if both players can afford it
            bets_forbidden = (self.stacks[0] == 0 or self.stacks[1] == 0)
            if bets_forbidden:
                return ['k']
            return ['k'] + raise_actions
        # continue_cost > 0
        # similarly, re-raising is only allowed if both players can afford it
        raises_forbidden = (continue_cost == self.stacks[active] or self.stacks[1-active] == 0)
        if raises_forbidden:
            return ['f', 'c']
        return ['f', 'c'] + raise_actions

    def raise_bounds(self):
        '''
        Returns a tuple of the minimum and maximum legal raises.
        '''
        active = self.button % 2
        continue_cost = self.pips[1-active] - self.pips[active]
        max_contribution = min(self.stacks[active], self.stacks[1-active] + continue_cost)
        min_contribution = min(max_contribution, continue_cost + max(continue_cost, BIG_BLIND))
        return (self.pips[active] + min_contribution, self.pips[active] + max_contribution)
            
    def proceed_street(self):
        '''
        Resets the players' pips and advances the game tree to the next round of betting.
        '''
        if self.street == 5:
            return self.showdown()
        new_street = 3 if self.street == 0 else self.street + 1
        new_hands = self.hands.copy()
        new_deck = eval7.Deck()
        new_deck.cards = self.deck[1].cards.copy()
        board = self.deck[0] + new_deck.deal(3 if self.street == 0 else 1)
        return RoundState(1, new_street, [0, 0], self.stacks, new_hands, (board, new_deck), self.history)

    def proceed(self, action):
        '''
        Advances the game tree by one action performed by the active player.
        '''
        active = self.button % 2
        if action == 'f':
            delta = self.stacks[0] - STARTING_STACK if active == 0 else STARTING_STACK - self.stacks[1]
            return TerminalState([delta, -delta])
        if action == 'c':
            if self.button == 0:  # sb calls bb
                return RoundState(1, 0, [BIG_BLIND] * 2, [STARTING_STACK - BIG_BLIND] * 2, self.hands, self.deck, self.history + action)
            # both players acted
            new_pips = list(self.pips)
            new_stacks = list(self.stacks)
            contribution = new_pips[1-active] - new_pips[active]
            new_stacks[active] -= contribution
            new_pips[active] += contribution
            state = RoundState(self.button + 1, self.street, new_pips, new_stacks, self.hands, self.deck, self.history + action)
            return state.proceed_street()
        if action == 'k':
            if (self.street == 0 and self.button > 0) or self.button > 1:  # both players acted
                state = RoundState(self.button + 1, self.street, self.pips, self.stacks, self.hands, self.deck, self.history + action)
                return state.proceed_street()
            # let opponent act
            return RoundState(self.button + 1, self.street, self.pips, self.stacks, self.hands, self.deck, self.history + action)
        # isinstance(action, RaiseAction)
        new_pips = list(self.pips)
        new_stacks = list(self.stacks)

        if action == 'a':
            raise_amount = self.raise_bounds()[1]
        else:
            continue_cost = self.pips[1-active] - self.pips[active]
            pot = 2 * STARTING_STACK - (self.stacks[0] + self.stacks[1])
            raise_amount = int(RAISES[RAISE_LETTER_INV[action]] * (pot + continue_cost)) + continue_cost + self.pips[active]

        contribution = raise_amount - new_pips[active]
        new_stacks[active] -= contribution
        new_pips[active] += contribution
        return RoundState(self.button + 1, self.street, new_pips, new_stacks, self.hands, self.deck, self.history + action)
