class Hud:

    def __init__(self):
        self.walks = 0  # number of rounds the SB (we) fold preflop when our opponent is the BB TODO: currently not updated
        self.vpip = 0  # number of rounds the opponent voluntarily puts chips into the pot preflop
        self.pfr = 0  # number of rounds the opponent raises preflop
        self.vpip_round = 0  # VPIP state for current round (0 or 1)
        self.pfr_round = 0  # PFR state for current round (0 or 1)

    def update_on_action(self, round_state, active):
        """
        Updates HUD stats. Called any time an action is needed.
        Returns boolean indicating whether or not Monte Carlo needs to be rerun.
        """
        street = round_state.street
        my_pip = round_state.pips[active]
        opp_pip = round_state.pips[1-active]
        continue_cost = opp_pip - my_pip

        recalc = False
        if street < 3:
            if active == 0: # the opp is BB
                if opp_pip > 2: # opp has voluntarily put chips in (responding to our raise / raising after limp)
                    if self.vpip_round == 0:
                        recalc = True
                    self.vpip_round = 1
                    if continue_cost > 0: # opp has raised in response to our raise / raised after limp
                        if self.pfr_round == 0:
                            recalc = True
                        self.pfr_round = 1
            else: # the opp is SB
                if opp_pip > 1:
                    if self.vpip_round == 0:
                        recalc = True
                    self.vpip_round = 1
                if continue_cost > 0: # opp has raised
                    if self.pfr_round == 0:
                        recalc = True
                    self.pfr_round = 1
                    
        if street == 3 and active == 0: # opp is BB, made it to the flop (neither of us folded)
            if continue_cost > 0 and my_pip == 0: # opp has made a cbet
                self.vpip_round = 1
        
        return recalc

    def update_after_round(self):
        self.vpip += self.vpip_round
        self.pfr += self.pfr_round
        self.vpip_round, self.pfr_round = 0, 0
