package mccfr;

import java.util.List;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Set;
import java.util.HashSet;
import java.util.Collections;
import java.lang.Integer;
import java.lang.String;

import poker.*;

/**
 * Encodes the game tree for one round of poker.
 */
public class RoundState {
    public static final int NUM_ROUNDS     = 1000;
    public static final int STARTING_STACK = 200;
    public static final int BIG_BLIND      = 2;
    public static final int SMALL_BLIND    = 1;
    public static final float[] RAISES     = {0.75f, 1.5f, 3f};
    
    public final int button;
    public final int street;
    public final List<Integer> pips;
    public final List<Integer> stacks;
    public final List<Hand> hands;
    public final Hand board;
    public final Deck deck;
    public final List<Action> history;
    public final List<Integer> deltas;

    public RoundState(int button, int street, List<Integer> pips, List<Integer> stacks,
                      List<Hand> hands, Hand board, Deck deck, List<Action> history, List<Integer> deltas) {
        this.button = button;
        this.street = street;
        this.pips = Collections.unmodifiableList(pips);
        this.stacks = Collections.unmodifiableList(stacks);
        this.hands = hands;
        this.board = board;
        this.deck = deck;
        this.history = Collections.unmodifiableList(history);
        this.deltas = Collections.unmodifiableList(deltas);
    }

    public RoundState() {
        this.button = 0;
        this.street = 0;
        this.pips = Collections.unmodifiableList(Arrays.asList(SMALL_BLIND, BIG_BLIND));
        this.stacks = Collections.unmodifiableList(Arrays.asList(STARTING_STACK - SMALL_BLIND, STARTING_STACK - BIG_BLIND));
        Deck deck = new Deck();
        deck.shuffle();
        Hand sbHand = new Hand(deck.nextcard(), deck.nextcard());
        Hand bbHand = new Hand(deck.nextcard(), deck.nextcard());
        this.hands = Arrays.asList(sbHand, bbHand);
        this.board = new Hand();
        this.deck = deck;
        this.history = Collections.unmodifiableList(Arrays.asList());
        this.deltas = Collections.unmodifiableList(Arrays.asList());
    }

    public RoundState(List<Integer> deltas) {
        this.button = -1;
        this.street = 0;
        this.pips = Collections.unmodifiableList(Arrays.asList());
        this.stacks = Collections.unmodifiableList(Arrays.asList());
        this.hands = Arrays.asList();
        this.board = new Hand();
        this.deck = new Deck();
        this.history = Collections.unmodifiableList(Arrays.asList());
        this.deltas = Collections.unmodifiableList(deltas);
    }

    public String getHistoryStr() {
        String output = "";
        for (Action a : this.history) {
            switch (a.actionType) {
                case FOLD_ACTION_TYPE: {
                    output += "f";
                    break;
                }
                case CALL_ACTION_TYPE: {
                    output += "c";
                    break;
                }
                case CHECK_ACTION_TYPE: {
                    output += "k";
                    break;
                }
                case RAISE0_ACTION_TYPE: {
                    output += "x";
                    break;
                }
                case RAISE1_ACTION_TYPE: {
                    output += "y";
                    break;
                }
                case RAISE2_ACTION_TYPE: {
                    output += "z";
                    break;
                }
                default: {
                    output += "a";
                    break;
                }
            }
        }
        return output;
    }

    public String getInfosetStr() {
        int active = this.button % 2;
        Hand hand = new Hand(this.hands.get(active));
        hand.addHand(this.board);
        int[] cardArray = new int[hand.getNumCards()];
        for (int i = 0; i < cardArray.length; i++) {
            Card c = hand.getCard(i);
            cardArray[i] = c.index();
        }
        String cardStr = "";
        if (street == 0) {
            cardStr = "P" + Global.indexer2.indexLast(cardArray);
        } else if (street == 3) {
            cardStr = "F" + Global.flopClusters[(int) Global.indexer23.indexLast(cardArray)];
        } else if (street == 4) {
            cardStr = "T" + Global.turnClusters[(int) Global.indexer24.indexLast(cardArray)];
        } else if (street == 5) {
            cardStr = "R" + Global.riverClusters[(int) Global.indexer25.indexLast(cardArray)];
        }
        return getHistoryStr() + cardStr;
    }

    /**
     * Compares the players' hands and computes payoffs.
     */
    public RoundState showdown() {
        Hand hand0 = new Hand(this.board);
        Hand hand1 = new Hand(this.board);
        hand0.addHand(this.hands.get(0));
        hand1.addHand(this.hands.get(1));
        int score0 = hand0.evaluate();
        int score1 = hand1.evaluate();
        int delta;
        if (score0 > score1) {
            delta = STARTING_STACK - this.stacks.get(1);
        } else if (score0 < score1) {
            delta = this.stacks.get(0) - STARTING_STACK;
        } else {
            delta = (this.stacks.get(0) - this.stacks.get(1)) / 2;
        }
        return new RoundState(Arrays.asList(delta, -delta));
    }

    public List<Action> getActions() {
        int active = this.button % 2;
        int continueCost = this.pips.get(1-active) - this.pips.get(active);

        List<Action> raiseActions = new ArrayList<Action>();
        boolean tooManyRaises = true;
        if (this.history.size() >= 5) {
            for (int i = 1; i <= 5; i++) {
                ActionType a = this.history.get(this.history.size() - i).actionType;
                if (!(a == ActionType.RAISE0_ACTION_TYPE || a == ActionType.RAISE1_ACTION_TYPE || 
                    a == ActionType.RAISE2_ACTION_TYPE || a == ActionType.ALLIN_ACTION_TYPE)) {
                    tooManyRaises = false;
                }
            }
        } else {
            tooManyRaises = false;
        }
        if (!tooManyRaises) {
            List<Integer> raiseBounds = this.raiseBounds();
            int minRaise = raiseBounds.get(0);
            int maxRaise = raiseBounds.get(1);
            for (int i = 0; i < RAISES.length; i++) {
                int pot = 2 * STARTING_STACK - (this.stacks.get(0) + this.stacks.get(1));
                int raiseAmount = (int) (RAISES[i] * (pot + continueCost)) + continueCost + this.pips.get(active);
                if (raiseAmount >= minRaise && raiseAmount < maxRaise) {
                    raiseActions.add(new Action(ActionType.valueOf("RAISE" + Integer.toString(i) + "_ACTION_TYPE"), raiseAmount));
                }
            }
            raiseActions.add(new Action(ActionType.ALLIN_ACTION_TYPE, maxRaise));
        }

        if (continueCost == 0) {
            // we can only raise the stakes if both players can afford it
            boolean betsForbidden = ((this.stacks.get(0) == 0) | (this.stacks.get(1) == 0));
            List<Action> actions = new ArrayList<Action>(Arrays.asList(new Action(ActionType.CHECK_ACTION_TYPE)));
            if (!betsForbidden) {
                actions.addAll(raiseActions);
            }
            return actions;
        }
        // continueCost > 0
        // similarly, re-raising is only allowed if both players can afford it
        boolean raisesForbidden = ((continueCost == this.stacks.get(active)) | (this.stacks.get(1-active) == 0));
        List<Action> actions = new ArrayList<Action>(Arrays.asList(new Action(ActionType.FOLD_ACTION_TYPE), new Action(ActionType.CALL_ACTION_TYPE)));
        if (!raisesForbidden) {
            actions.addAll(raiseActions);
        }
        return actions;
    }

    /**
     * Returns a list of the minimum and maximum legal raises.
     */
    public List<Integer> raiseBounds() {
        int active = this.button % 2;
        int continueCost = this.pips.get(1-active) - this.pips.get(active);
        int maxContribution = Math.min(this.stacks.get(active), this.stacks.get(1-active) + continueCost);
        int minContribution = Math.min(maxContribution, continueCost + Math.max(continueCost, BIG_BLIND));
        return Arrays.asList(this.pips.get(active) + minContribution, this.pips.get(active) + maxContribution);
    }

    /**
     * Resets the players' pips and advances the game tree to the next round of betting.
     */
    public RoundState proceedStreet() {
        if (this.street == 5) {
            return this.showdown();
        }
        int newStreet;
        if (this.street == 0) {
            newStreet = 3;
        } else {
            newStreet = this.street + 1;
        }
        Deck newDeck = new Deck(this.deck);
        Hand newBoard = new Hand(this.board);
        if (this.street == 0) {
            for (int i = 0; i < 3; i++) {
                newBoard.addCard(newDeck.nextcard());
            }
        } else {
            newBoard.addCard(newDeck.nextcard());
        }
        return new RoundState(1, newStreet, Arrays.asList(0, 0), this.stacks, this.hands, newBoard, newDeck, this.history, this.deltas);
    }

    /**
     * Advances the game tree by one action performed by the active player.
     */
    public RoundState proceed(Action action) {
        int active = this.button % 2;
        List<Action> newHistory = new ArrayList<Action>(this.history);
        newHistory.add(action);

        switch (action.actionType) {
            case FOLD_ACTION_TYPE: {
                int delta;
                if (active == 0) {
                    delta = this.stacks.get(0) - STARTING_STACK;
                } else {
                    delta = STARTING_STACK - this.stacks.get(1);
                }
                return new RoundState(Arrays.asList(delta, -1 * delta));
            }
            case CALL_ACTION_TYPE: {
                if (this.button == 0) {  // sb calls bb
                    return new RoundState(1, 0, Arrays.asList(BIG_BLIND, BIG_BLIND),
                                          Arrays.asList(STARTING_STACK - BIG_BLIND,
                                                        STARTING_STACK - BIG_BLIND),
                                          this.hands, this.board, this.deck, newHistory, this.deltas);
                }
                // both players acted
                List<Integer> newPips = new ArrayList<Integer>(this.pips);
                List<Integer> newStacks = new ArrayList<Integer>(this.stacks);
                int contribution = newPips.get(1-active) - newPips.get(active);
                newStacks.set(active, newStacks.get(active) - contribution);
                newPips.set(active, newPips.get(active) + contribution);
                RoundState state = new RoundState(this.button + 1, this.street, newPips, newStacks,
                                                  this.hands, this.board, this.deck, newHistory, this.deltas);
                return state.proceedStreet();
            }
            case CHECK_ACTION_TYPE: {
                if (((this.street == 0) & (this.button > 0)) | (this.button > 1)) {  // both players acted
                    RoundState state = new RoundState(this.button + 1, this.street, this.pips, this.stacks,
                                                      this.hands, this.board, this.deck, newHistory, this.deltas);
                    return state.proceedStreet();
                }
                // let opponent act
                return new RoundState(this.button + 1, this.street, this.pips, this.stacks, this.hands, this.board, this.deck, newHistory, this.deltas);
            }
            default: {  // RAISE_ACTION_TYPE
                List<Integer> newPips = new ArrayList<Integer>(this.pips);
                List<Integer> newStacks = new ArrayList<Integer>(this.stacks);
                int contribution = action.amount - newPips.get(active);
                newStacks.set(active, newStacks.get(active) - contribution);
                newPips.set(active, newPips.get(active) + contribution);
                return new RoundState(this.button + 1, this.street, newPips, newStacks, this.hands, this.board, this.deck, newHistory, this.deltas);
            }
        }
    }
}