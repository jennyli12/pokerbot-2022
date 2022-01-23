'''
MCCFR finally.
'''
from ast import Call
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import pickle
import numpy as np
import random

from hand_indexer import HandIndexer
from util import get_abstract_actions

RAISES = [0.75, 1.5, 3]  # percentage of pot for raise
RAISE_LETTER = ['x', 'y', 'z']
RAISE_LETTER_INV = {'x': 0, 'y': 1, 'z': 2}
RAISE_SET = {'x', 'y', 'z', 'a'}

RANK = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
SUIT = {'s': 0, 'h': 1, 'd': 2, 'c': 3}


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        self.fold_rest = False  # True if we have sealed victory (can check-fold the rest of the hands)
        self.street_tracker = 0  # updates to the street at the end of each action (used to check if the street has just changed)

        # with open('avgstrategy.pickle', 'rb') as f:
        #     self.strategy_map = pickle.load(f)  # infoset str -> list of action probablities

        self.indexer_2 = HandIndexer([2])
        self.indexer_2_3 = HandIndexer([2, 3])
        self.indexer_2_4 = HandIndexer([2, 4])
        self.indexer_2_5 = HandIndexer([2, 5])

        self.flop_clusters = np.load('flop_clusters.npy')
        self.turn_clusters = np.load('turn_clusters.npy')
        self.river_clusters = np.load('river_clusters.npy')

        self.history = ""

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        # game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind

        rounds_left = NUM_ROUNDS - round_num + 1
        will_lose = rounds_left * (BIG_BLIND + SMALL_BLIND) + (rounds_left % 2) * (BIG_BLIND - SMALL_BLIND if big_blind else SMALL_BLIND - BIG_BLIND)
        if 2 * my_bankroll > will_lose and not self.fold_rest:
            self.fold_rest = True
            print("Sealed win on round", round_num)

        self.history = ""
        self.street_tracker = 0
        self.card_str_tracker = ""

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        # my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        # previous_state = terminal_state.previous_state  # RoundState before payoffs
        # street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        # my_cards = previous_state.hands[active]  # your cards
        # opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed
        
        if game_state.round_num == NUM_ROUNDS:
            print("Game clock", game_state.game_clock)

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        street = round_state.street  # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        # if RaiseAction in legal_actions:
        #    min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise
        #    min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
        #    max_cost = max_raise - my_pip  # the cost of a maximum bet/raise

        if self.fold_rest:  # check-fold
            if CheckAction in legal_actions:
                return CheckAction()
            return FoldAction()
        
        # self.history stores abstract history
        check_option, call_option = False, False  # determines if a raise can be mapped to a check or call
        if active:  # BB
            if self.history == '' and street == 3:  # handle special case where sb first action raised is mapped to a call
                self.history = 'ck'
            if self.history == '':  # I have not acted yet
                opp = 'c' if continue_cost == 0 else 'r'
                call_option = True
            elif self.history[-1] == 'k':  # I just checked
                if street != self.street_tracker:
                    opp = '' if street == 3 else 'k'
                else:
                    opp = 'r'
                    check_option = True
            elif self.history[-1] == 'c':  # I just called
                opp = ''
            else:  # I just raised
                opp = 'c' if street != self.street_tracker else 'r'
                call_option = True
        else:  # SB
            if self.history == '':
                opp = ''
            elif self.history[-1] == 'k':
                opp = 'k' if continue_cost == 0 else 'r'
                check_option = True
            elif self.history[-1] == 'c':
                if street == 3 and self.history == 'c':
                    opp = 'kk' if continue_cost == 0 else 'kr'
                else:
                    opp = 'k' if continue_cost == 0 else 'r'
                check_option = True
            else:
                if street != self.street_tracker:
                    opp = 'ck' if continue_cost == 0 else 'cr'
                    check_option = True
                else:
                    opp = 'r'
                    call_option = True

        # real lower than abstract -> abstract may be x, y, a but actually x, y, z, a allowed
        # real higher than abstract -> abstract may be x, y, z, a but actually x, y, a

        map_call, map_check, map_all_in = False, False, False
        if len(opp) > 0 and opp[-1] == 'r':
            letters, raise_sizes = [], []
            if check_option:
                letters.append('k')
                raise_sizes.append(0)
            elif call_option:
                letters.append('c')
                raise_sizes.append(0)
            abstract_actions = get_abstract_actions(self.history + opp[:-1])  # opp, prevents missing infoset
            all_in = (STARTING_STACK - my_contribution) / (my_contribution + opp_contribution - continue_cost)
            for i in range(len(RAISES)):
                if RAISES[i] < all_in and RAISE_LETTER[i] in abstract_actions:
                    letters.append(RAISE_LETTER[i])
                    raise_sizes.append(RAISES[i])
            letters.append('a')
            raise_sizes.append(all_in)

            x = continue_cost / (my_contribution + opp_contribution - continue_cost)
            i = 0
            while i < len(raise_sizes) and x >= raise_sizes[i]:
                i += 1
            if i == 0:
                mapped = letters[0]
            elif i == len(raise_sizes):
                mapped = letters[-1]
            else:
                A, B = raise_sizes[i - 1], raise_sizes[i]
                f = (B - x) * (1 + A) / ((B - A) * (1 + x))
                mapped = letters[i - 1] if random.random() < f else letters[i]
            if mapped == 'k':
                map_check = True
            elif mapped == 'c':
                map_call = True
            elif mapped == 'a' and STARTING_STACK - my_contribution != continue_cost:
                map_all_in = True
            opp = opp[:-1] + mapped

        self.history += opp

        def get_card_index(card):
            rank = RANK[card[0]]
            suit = SUIT[card[1]]
            return rank * 4 + suit

        cards = my_cards + board_cards
        card_array = [get_card_index(str(card)) for card in cards]
        if street == 0:
            card_str = 'P' + str(self.indexer_2.index_last(card_array))
        elif street == 3:
            card_str = 'F' + str(self.flop_clusters[self.indexer_2_3.index_last(card_array)])
        elif street == 4:
            card_str = 'T' + str(self.turn_clusters[self.indexer_2_4.index_last(card_array)])
        else:
            card_str = 'R' + str(self.river_clusters[self.indexer_2_5.index_last(card_array)])
        infoset_str = self.history + card_str

        print(game_state.round_num, infoset_str)
        
        if card_str != self.card_str_tracker:
            with open(f'avgstrategy/{card_str}.pickle', 'rb') as f:
                self.strategy_map = pickle.load(f)

        self.card_str_tracker = card_str
        

        # if raises are limited in abstract, only consider those in abstract
        # if raises are limited in real, combine with all-in (if [x, a] in real, a prob should be y + z + a in abstract)
        # if prev opp raise mapped to a check, k probability is now for calling (add k to history), r prob is same, automatic call if sb k
        # if prev opp raise < all-in mapped to all-in, c probability is now for all-in (have to end betting in this street), 
        # add c to history
        # if prev opp raise mapped to a call, automatically call, add nothing to history

        if (map_check and active) or map_call or (map_check and self.history == 'ck'):
            self.history = self.history[:-1]
            return CallAction()  # add nothing to history

        if infoset_str not in self.strategy_map:
            print("Infoset not found")
            choice = 'k' if CheckAction in legal_actions else 'f'
        else:
            probabilities = self.strategy_map[infoset_str]
            my_abstract_actions = get_abstract_actions(self.history)
            print(my_abstract_actions, probabilities)
            strategy = {}
            for i in range(len(my_abstract_actions)):
                strategy[my_abstract_actions[i]] = probabilities[i]

            if 'f' in strategy and strategy['f'] > 0.8:
                choice = 'f'
            else:
                combined_strategy = {'b': 0}
                bets = {}
                for s in strategy:
                    if s in RAISE_SET:
                        combined_strategy['b'] += strategy[s]
                        bets[s] = strategy[s]
                    else:
                        combined_strategy[s] = strategy[s]
                choice = max(combined_strategy, key=combined_strategy.get)
                if choice == 'b':
                    choice = max(bets, key=bets.get)

        my_action = None
        if choice == 'k':
            if map_check and infoset_str in self.strategy_map:
                my_action = CallAction()
            else:
                my_action = CheckAction()
        elif choice == 'f':
            my_action = FoldAction()
        elif choice == 'c':
            if map_all_in:
                my_action = RaiseAction(round_state.raise_bounds()[1])
            else:
                my_action = CallAction()
        else:
            if RaiseAction in legal_actions:
                min_raise, max_raise = round_state.raise_bounds()
                if choice == 'a':
                    raise_amount = max_raise
                else:
                    pot = my_contribution + opp_contribution
                    raise_amount = int(RAISES[RAISE_LETTER_INV[choice]] * (pot + continue_cost)) + continue_cost + my_pip
                    raise_amount = min(max(raise_amount, min_raise), max_raise)  # change history if all-in?
                my_action = RaiseAction(raise_amount)
            elif CallAction in legal_actions:
                my_action = CallAction()
            elif CheckAction in legal_actions:
                my_action = CheckAction()

        self.street_tracker = street
        self.history += choice
        return my_action


if __name__ == '__main__':
    run_bot(Player(), parse_args())
