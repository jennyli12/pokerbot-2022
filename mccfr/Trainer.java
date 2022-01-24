package mccfr;

import java.util.List;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.Random;

import poker.*;

public class Trainer {
    public static final int REGRET_FLOOR = -110000;
    public static final int PRUNE_BOUND = -100000;

    public static final String RESET = "\033[0m";
    public static final String RED = "\033[0;31m";
    public static final String GREEN = "\033[0;32m";
    public static final String RED_BRIGHT = "\033[0;91m";
    public static final String GREEN_BRIGHT = "\033[0;92m";

    public Trainer() {
    }

    public static int sampleDistribution(float[] probabilities) {
        double rand = new Random().nextDouble();
        double sum = 0.0;
        for (int i = 0; i < probabilities.length; i++)
        {
            sum += probabilities[i];
            if (sum >= rand)
            {
                return i;
            }
        }
        return probabilities.length - 1;
    } 

    public void updateStrategy(RoundState state, int traverser) {
        if (state.button == -1) {
            return;
        }
        List<Action> actions = state.getActions();
        int active = state.button % 2;
        if (traverser == active) {
            String infosetStr = state.getInfosetStr();
            Infoset infoset = Global.nodeMap.get(infosetStr);
            if (infoset == null) {
                infoset = new Infoset(actions.size());
                Global.nodeMap.put(infosetStr, infoset);
            }
            float[] strategy = infoset.getStrategy();
            int i = sampleDistribution(strategy);
            infoset.cumulStrategy[i]++;
            updateStrategy(state.proceed(actions.get(i)), traverser);
        } else {
            for (int i = 0; i < actions.size(); i++) {
                updateStrategy(state.proceed(actions.get(i)), traverser);
            }
        }
    }

    public float cfr(RoundState state, int traverser, boolean prune) {
        if (state.button == -1) {
            return state.deltas.get(traverser);
        }
        List<Action> actions = state.getActions();
        String infosetStr = state.getInfosetStr();
        Infoset infoset = Global.nodeMap.get(infosetStr);
        if (infoset == null) {
            infoset = new Infoset(actions.size());
            Global.nodeMap.put(infosetStr, infoset);
        }
        float[] strategy = infoset.getStrategy();
        int active = state.button % 2;
        if (traverser == active) {
            float[] utils = new float[actions.size()];
            float nodeUtil = 0.0f;
            if (prune && state.street != 5) {
                boolean[] explored = new boolean[actions.size()];
                for (int i = 0; i < actions.size(); i++) {
                    if (infoset.cumulRegret[i] > PRUNE_BOUND) {
                        utils[i] = cfr(state.proceed(actions.get(i)), traverser, prune);
                        explored[i] = true;
                        nodeUtil += strategy[i] * utils[i];
                    } else {
                        explored[i] = false;
                    }
                }
                for (int i = 0; i < actions.size(); i++) {
                    if (explored[i]) {
                        infoset.cumulRegret[i] += utils[i] - nodeUtil;
                        infoset.cumulRegret[i] = Math.max(REGRET_FLOOR, infoset.cumulRegret[i]);
                    }
                }
            } else {
                for (int i = 0; i < actions.size(); i++) {
                    utils[i] = cfr(state.proceed(actions.get(i)), traverser, prune);
                    nodeUtil += strategy[i] * utils[i];
                }
                for (int i = 0; i < actions.size(); i++) {
                    infoset.cumulRegret[i] += utils[i] - nodeUtil;
                    infoset.cumulRegret[i] = Math.max(REGRET_FLOOR, infoset.cumulRegret[i]);
                }
            }
            return nodeUtil;
        } else {
            int i = sampleDistribution(strategy);
            float util = cfr(state.proceed(actions.get(i)), traverser, prune);
            return util;
        }
    }

    public void discountInfosets(float d) {
        for (Infoset infoset : Global.nodeMap.values()) {
            for (int i = 0; i < infoset.cumulRegret.length; i++) {
                infoset.cumulRegret[i] *= d;
                infoset.cumulStrategy[i] *= d;
            }
        }
    }

    public List<RoundState> getFirstActionStates() {
        List<RoundState> states = new ArrayList<RoundState>();
        for (int i = 0; i < 169; i++) {
            int rank1 = i / 13;
            int rank2 = i % 13;
            int suit1 = 3;
            int suit2;
            if (rank2 > rank1) {
                suit2 = 3;
            } else {
                suit2 = 2;
            }
            Hand sbHand = new Hand(13 * suit1 + rank1, 13 * suit2 + rank2);
            Deck deck = new Deck();
            deck.removeCards(sbHand);
            deck.shuffle();
            Hand bbHand = new Hand(deck.nextcard(), deck.nextcard());
            List<Integer> pips = Arrays.asList(RoundState.SMALL_BLIND, RoundState.BIG_BLIND);
            List<Integer> stacks = Arrays.asList(RoundState.STARTING_STACK - RoundState.SMALL_BLIND, RoundState.STARTING_STACK - RoundState.BIG_BLIND);
            List<Hand> hands = Arrays.asList(sbHand, bbHand);
            states.add(new RoundState(0, 0, pips, stacks, hands, new Hand(), deck, Arrays.asList(), Arrays.asList()));
        }
        return states;
    }

    public void printStartingHandsChart() {
        List<RoundState> states = getFirstActionStates();
        List<Action> actions = states.get(0).getActions();
        for (int i = 0; i < actions.size(); i++) {
            Action action = actions.get(i);
            System.out.println(action.actionType);
            System.out.println("    2    3    4    5    6    7    8    9    T    J    Q    K    A (suited)");
            for (int j = 0; j < states.size(); j++) {
                RoundState state = states.get(j);
                String infosetStr = state.getInfosetStr();
                Infoset infoset = Global.nodeMap.get(infosetStr);
                if (infoset == null) {
                    infoset = new Infoset(actions.size());
                    Global.nodeMap.put(infosetStr, infoset);
                }
                float[] phi = infoset.getAverageStrategy();
                if (j % 13 == 0 && j + 1 < states.size()) {
                    if (j / 13 < 8) {
                        System.out.print((j / 13 + 2) + " ");
                    } else if (j / 13 == 8) {
                        System.out.print("T ");
                    } else if (j / 13 == 9) {
                        System.out.print("J ");
                    } else if (j / 13 == 10) {
                        System.out.print("Q ");
                    } else if (j / 13 == 11) {
                        System.out.print("K ");
                    } else {
                        System.out.print("A ");
                    }
                }
                String string = String.format("%.2f", phi[i]) + " ";
                if (phi[i] <= 0.25) {
                    System.out.print(RED_BRIGHT + string + RESET);
                } else if (phi[i] <= 0.5) {
                    System.out.print(RED + string + RESET);
                } else if (phi[i] <= 0.75) {
                    System.out.print(GREEN + string + RESET);
                } else {
                    System.out.print(GREEN_BRIGHT + string + RESET);
                }
                if ((j + 1) % 13 == 0) {
                    System.out.println();
                }
            }
        }
    }
}