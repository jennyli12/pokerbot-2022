'''
Minor experiments/changes from bot2.
Final bot does the following different from before:
No bluffing
Changes sb preflop strategy dep on opponent pfr
More aggressive when checked to esp on turn/river
Much looser when cbet to (common strat this year)
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

from equity import EquityCalculator
from hud import Hud
from strategy import Strategy


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
        self.equity_calculator = None  # EquityCalculator object (new one for each round)
        self.hud = Hud()
        self.strategy = Strategy(self.hud)
        self.fold_rest = False  # True if we have sealed victory (can check-fold the rest of the hands)
        self.street_tracker = 0  # updates to the street at the end of each action (used to check if the street has just changed)

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

        self.equity_calculator = EquityCalculator(my_cards)

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
        
        self.strategy.update_after_round(terminal_state, active)
        self.street_tracker = 0
        self.hud.update_after_round()

        if game_state.round_num == NUM_ROUNDS:
            print("Game clock", game_state.game_clock)
            print("Walks/VPIP/PFR", self.hud.walks, self.hud.vpip, self.hud.pfr)

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
        # my_cards = round_state.hands[active]  # your cards
        # board_cards = round_state.deck[:street]  # the board cards
        # my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        # opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        # my_stack = round_state.stacks[active]  # the number of chips you have remaining
        # opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        # continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        # my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        # opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        # if RaiseAction in legal_actions:
        #    min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise
        #    min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
        #    max_cost = max_raise - my_pip  # the cost of a maximum bet/raise
        
        my_action = None

        if self.fold_rest:  # check-fold
            if CheckAction in legal_actions:
                my_action = CheckAction()
            else:
                my_action = FoldAction()
        
        else:
            recalc = self.hud.update_on_action(round_state, active)
            if street != self.street_tracker or recalc:
                self.equity_calculator.run_monte_carlo(game_state, round_state, active, self.hud)
            print("Round", game_state.round_num, "| Street", street, "| Equity", "{:.3f}".format(self.equity_calculator.equity))

            my_action = self.strategy.play(game_state, round_state, active, self.equity_calculator.equity)
        
        self.street_tracker = street
        return my_action


if __name__ == '__main__':
    run_bot(Player(), parse_args())
