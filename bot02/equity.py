from eval7 import Card, HandRange, py_hand_vs_range_monte_carlo

# eval7 HandRanges are weighted ranges of hands: https://github.com/julianandrews/pyeval7/blob/master/eval7/handrange.py
# Note that .hands is a list of (hand, weight) tuples where a hand is a tuple of 2 eval7 Cards
ALL_HANDS = HandRange("22+, A2+, K2+, Q2+, J2+, T2+, 92+, 82+, 72+, 62+, 52+, 42+, 32+")

# Sklansky-Karlson rankings of the 169 possible starting hands based on heads-up strength
SKLANSKY_KARLSON = ['AA', 'KK', 'AKs', 'QQ', 'AKo', 'JJ', 'AQs', 'TT', 'AQo', '99', 'AJs', '88', 'ATs', 'AJo', 
                    '77', '66', 'ATo', 'A9s', '55', 'A8s', 'KQs', '44', 'A9o', 'A7s', 'KJs', 'A5s', 'A8o', 
                    'A6s', 'A4s', '33', 'KTs', 'A7o', 'A3s', 'KQo', 'A2s', 'A5o', 'A6o', 'A4o', 'KJo', 'QJs', 
                    'A3o', '22', 'K9s', 'A2o', 'KTo', 'QTs', 'K8s', 'K7s', 'JTs', 'K9o', 'K6s', 'QJo', 'Q9s', 
                    'K5s', 'K8o', 'K4s', 'QTo', 'K7o', 'K3s', 'K2s', 'Q8s', 'K6o', 'J9s', 'K5o', 'Q9o', 'JTo', 
                    'K4o', 'Q7s', 'T9s', 'Q6s', 'K3o', 'J8s', 'Q5s', 'K2o', 'Q8o', 'Q4s', 'J9o', 'Q3s', 'T8s', 
                    'J7s', 'Q7o', 'Q2s', 'Q6o', '98s', 'Q5o', 'J8o', 'T9o', 'J6s', 'T7s', 'J5s', 'Q4o', 'J4s', 
                    'J7o', 'Q3o', '97s', 'T8o', 'J3s', 'T6s', 'Q2o', 'J2s', '87s', 'J6o', '98o', 'T7o', '96s', 
                    'J5o', 'T5s', 'T4s', '86s', 'J4o', 'T6o', '97o', 'T3s', '76s', '95s', 'J3o', 'T2s', '87o', 
                    '85s', '96o', 'T5o', 'J2o', '75s', '94s', 'T4o', '65s', '86o', '93s', '84s', '95o', 'T3o', 
                    '76o', '92s', '74s', '54s', 'T2o', '85o', '64s', '83s', '94o', '75o', '82s', '73s', '93o', 
                    '65o', '53s', '63s', '84o', '92o', '43s', '74o', '72s', '54o', '64o', '52s', '62s', '83o', 
                    '42s', '82o', '73o', '53o', '63o', '32s', '43o', '72o', '52o', '62o', '42o', '32o']


# pre-calculated ranges
# RANGES[round(% * 1326)] returns the top % of hands as a list of (hand, weight) tuples
RANGES = [HandRange("AA").hands] * 7
for hand_type in SKLANSKY_KARLSON[1:]:
    hands = HandRange(hand_type).hands
    cumulative_hands = RANGES[-1] + hands
    for _ in range(len(hands)):
        RANGES.append(cumulative_hands)
print("Range pre-calculation complete")


def remove_cards_from_range(range, cards):
    cards = set(map(Card, cards))
    return [hand for hand in range if hand[0][0] not in cards and hand[0][1] not in cards]


class EquityCalculator:

    def __init__(self, my_cards):
        self.opp_range = remove_cards_from_range(ALL_HANDS.hands, my_cards)  # list of (hand, weight) tuples describing the opponent's range
        self.equity = py_hand_vs_range_monte_carlo(map(Card, my_cards), self.opp_range, [], 5000)  # decimal representing odds we'll win against the opponent's range
        self.original_cards = my_cards

    def run_monte_carlo(self, game_state, round_state, active, hud):
        """
        Reruns Monte Carlo.
        """
        street = round_state.street
        my_cards = round_state.hands[active]
        board_cards = round_state.deck[:street]

        if game_state.round_num > 50 and street <= 3:
            if hud.pfr_round == 1:
                percentage = hud.pfr / (game_state.round_num - 1 - hud.walks)
                self.opp_range = RANGES[round(percentage * 1326)]
                print("Opp range", "{:.3f}".format(percentage))
            elif hud.vpip_round == 1:
                percentage = hud.vpip / (game_state.round_num - 1 - hud.walks)
                self.opp_range = RANGES[round(percentage * 1326)]
                print("Opp range", "{:.3f}".format(percentage))

        self.opp_range = remove_cards_from_range(self.opp_range, my_cards + board_cards + self.original_cards)
        # TODO: need to run MC without the self.original cards in the deck
        self.equity = py_hand_vs_range_monte_carlo(map(Card, my_cards), self.opp_range, list(map(Card, board_cards)), 5000)
