from collections import namedtuple

STARTING_STACK = 200
BIG_BLIND = 2
SMALL_BLIND = 1

RAISES = [0.75, 1.5, 3]  # percentage of pot for raise
RAISE_LETTER = ['x', 'y', 'z']
RAISE_LETTER_INV = {'x': 0, 'y': 1, 'z': 2}
RAISE_SET = {'x', 'y', 'z', 'a'}

def get_abstract_actions(history):
    state = AbstractState(0, 0, [SMALL_BLIND, BIG_BLIND], [STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND], "")
    for action in history:
        state = state.proceed(action)
    if state is None:
        return []
    return state.get_actions()

class AbstractState(namedtuple('_AbstractRoundState', ['button', 'street', 'pips', 'stacks', 'history'])):

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
            return None
        new_street = 3 if self.street == 0 else self.street + 1
        return AbstractState(1, new_street, [0, 0], self.stacks, self.history)

    def proceed(self, action):
        '''
        Advances the game tree by one action performed by the active player.
        '''
        active = self.button % 2
        if action == 'f':
            return None
        if action == 'c':
            if self.button == 0:  # sb calls bb
                return AbstractState(1, 0, [BIG_BLIND] * 2, [STARTING_STACK - BIG_BLIND] * 2, self.history + action)
            # both players acted
            new_pips = list(self.pips)
            new_stacks = list(self.stacks)
            contribution = new_pips[1-active] - new_pips[active]
            new_stacks[active] -= contribution
            new_pips[active] += contribution
            state = AbstractState(self.button + 1, self.street, new_pips, new_stacks, self.history + action)
            return state.proceed_street()
        if action == 'k':
            if (self.street == 0 and self.button > 0) or self.button > 1:  # both players acted
                state = AbstractState(self.button + 1, self.street, self.pips, self.stacks, self.history + action)
                return state.proceed_street()
            # let opponent act
            return AbstractState(self.button + 1, self.street, self.pips, self.stacks, self.history + action)
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
        return AbstractState(self.button + 1, self.street, new_pips, new_stacks, self.history + action)
