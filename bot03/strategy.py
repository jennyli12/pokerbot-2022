from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import STARTING_STACK
import random

class Strategy:
    
    def __init__(self, hud):
        self.just_bluffed = False
        self.times_called_bluff = 0
        self.times_bluff_succeeded = 0
        self.hud = hud
        self.cbets = 0
        self.cbet_opps = 0

        self.pf_tightness = 0.55  # tune 0.6
        self.tightness = 0.75  # tune 0.69

    def play(self, game_state, round_state, active, strength):
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        street = round_state.street  # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise

        if street < 3 and my_pip == 1 and active == 0 and strength < self.pf_tightness:  # sb pre-flop 1st action, limp if s < pf_tightness
            pfr_percent = self.hud.pfr / (game_state.round_num - self.hud.walks)
            if CallAction in legal_actions and continue_cost <= my_stack and strength > min(0.5, pfr_percent):
                return CallAction()
            else:
                self.hud.walks += 1
                return FoldAction()

        # raise_bluff = True
        # if not (self.times_called_bluff > 1 and self.times_bluff_succeeded / self.times_called_bluff < 7) and not self.just_bluffed:  # tune
        #     if active == 0 and legal_actions == {CheckAction, RaiseAction} and strength < self.tightness:
        #         if street == 5 or random.random() < 0.1:
        #             max_cost = min(max_raise - my_pip, my_stack)
        #             if max_cost + my_pip > 100:  # tune
        #                 self.just_bluffed = True
        #                 print("Bluffed on round", game_state.round_num)
        #                 return RaiseAction(101)  # tune! (max_cost + my_pip)
        #             else:
        #                 raise_bluff = False
        #         elif raise_bluff: 
        #             raise_factor = 3 if street == 3 else 5
        #             raise_amount = raise_factor * min_raise
        #             if raise_amount - my_pip <= my_stack:
        #                 return RaiseAction(raise_amount)
        
        tightness = self.pf_tightness if street == 0 else self.tightness
        pot = my_contribution + opp_contribution

        if continue_cost == 0:
            if street == 3:
                if active == 0:
                    tightness -= 0.05
            if street == 4:
                if active == 0 and pot < 20:
                    tightness -= 0.1
                elif active == 0:
                    tightness -= 0.05
            if street == 5:
                if active == 0 and pot < 30:
                    tightness -= 0.4
                elif active == 0:
                    tightness -= 0.2

        if street == 3 and active == 0 and my_pip == 0:
            self.cbet_opps += 1
            if continue_cost > 0 and continue_cost < 20:
                self.cbets += 1
                cbet_percent = self.cbets / self.cbet_opps
                print('CB%', cbet_percent)
                tightness -= cbet_percent/2
        
        if strength > min(0.75 + street * 0.04, tightness + pot/1300):  # tune
            raise_amount = int(my_pip + continue_cost + (strength - 0.1) * (pot + continue_cost))
            raise_amount = min(max(raise_amount, min_raise), max_raise)

            if RaiseAction in legal_actions and raise_amount - my_pip <= my_stack:
                return RaiseAction(raise_amount)
            elif CallAction in legal_actions and continue_cost <= my_stack:
                return CallAction()
            elif CheckAction in legal_actions:
                return CheckAction()
            else:
                return FoldAction()

        # if strength > tightness - 0.05 + pot/1000:
        #     if CallAction in legal_actions and continue_cost <= my_stack:
        #         return CallAction()
        #     elif CheckAction in legal_actions:
        #         return CheckAction()
        #     else:
        #         return FoldAction()

        if continue_cost > 0:
            pot_odds = continue_cost / (pot + continue_cost)
            if strength > pot_odds:  # tune
                if continue_cost >= 0:  # tune
                    if strength > min(0.7 + street * 0.04, tightness - 0.1 + pot/1300) or (strength > 2 * pot_odds + 0.1 and continue_cost < 70):
                        if continue_cost <= my_stack:
                            return CallAction()
                        return FoldAction()
                    return FoldAction()
                return CallAction()
            return FoldAction()
        return CheckAction()

    def update_after_round(self, terminal_state, active):
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed
        
        if self.just_bluffed:
            self.just_bluffed = False
            if opp_cards:
                print("BLUFF CALLED")
                self.times_called_bluff += 1
            else:
                self.times_bluff_succeeded += 1
                print("BLUFF SUCCEEDED")
