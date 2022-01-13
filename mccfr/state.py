from collections import namedtuple
import eval7
# import random

# TODO: swaps (need to store if a swap occurred)
# FLOP_PERCENT = 0.1
# TURN_PERCENT = 0.05
STARTING_STACK = 200
BIG_BLIND = 2
SMALL_BLIND = 1

RAISES = [0.75, 1]  # percentage of pot for r0 / r1

TerminalState = namedtuple('TerminalState', ['deltas'])


def get_root_state():
    deck = eval7.Deck()
    deck.shuffle()
    deck = ([], deck)
    hands = [deck[1].deal(2), deck[1].deal(2)]
    pips = [SMALL_BLIND, BIG_BLIND]
    stacks = [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND]
    return RoundState(0, 0, pips, stacks, hands, deck, "")

# def swap(player_card_index, hands, deck):
#     '''
#     Swaps player's card with a card from the deck.
#     '''
#     card_index = player_card_index % len(hands)
#     player_index = player_card_index // len(hands)
#     random_card = deck.deal(1)
#     deck.cards.append(hands[player_index][card_index])
#     hands[player_index][card_index] = random_card[0]
#     return hands, deck

class RoundState(namedtuple('_RoundState', ['button', 'street', 'pips', 'stacks', 'hands', 'deck', 'history'])):
    '''
    Encodes the game tree for one round of poker.
    '''

    def get_infoset_str(self):
        active = self.button % 2
        cards = self.hands[active] + self.deck[0]
        index = "".join([str(c) for c in cards])  # TODO: indexing function
        street_str = {0: 'P', 3: 'F', 4: 'T', 5: 'R'}
        return self.history + street_str[self.street] + index

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

        min_raise, max_raise = self.raise_bounds()
        raise_actions = []
        for i in range(len(RAISES)):
            raise_amount = RAISES[i] * 2 * self.pips[1-active] + continue_cost
            if raise_amount >= min_raise and raise_amount < max_raise:
                raise_actions.append('r' + str(i))
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
        # if self.street == 0 or self.street == 3:
        #     for i in range(sum([len(hand) for hand in self.hands])):
        #         if random.random() < (FLOP_PERCENT if self.street == 0 else TURN_PERCENT):
        #             new_hands, new_deck = swap(i, new_hands, new_deck)
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
                return self.proceed_street()
            # let opponent act
            return RoundState(self.button + 1, self.street, self.pips, self.stacks, self.hands, self.deck, self.history + action)
        # isinstance(action, RaiseAction)
        new_pips = list(self.pips)
        new_stacks = list(self.stacks)

        if action == 'a':
            raise_amount = self.raise_bounds()[1]
        else:
            continue_cost = self.pips[1-active] - self.pips[active]
            raise_amount = RAISES[int(action[-1])] * 2 * self.pips[1-active] + continue_cost

        contribution = raise_amount - new_pips[active]
        new_stacks[active] -= contribution
        new_pips[active] += contribution
        return RoundState(self.button + 1, self.street, new_pips, new_stacks, self.hands, self.deck, self.history + action)
