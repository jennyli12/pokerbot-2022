package mccfr;

import java.io.Serializable;

public class Infoset implements Serializable {
    public float[] cumulRegret;
    public float[] cumulStrategy;

    public Infoset(int numActions) {
        cumulRegret = new float[numActions];
        cumulStrategy = new float[numActions];
    }

    public float[] getStrategy() {
        float normalizingSum = 0;
        float[] strategy = new float[cumulRegret.length];
        for (int i = 0; i < cumulRegret.length; i++) {
            normalizingSum += Math.max(0, cumulRegret[i]);
        }
        for (int i = 0; i < cumulRegret.length; i++) {
            if (normalizingSum > 0) {
                strategy[i] = Math.max(0, cumulRegret[i] / normalizingSum);
            } else {
                strategy[i] = 1.0f / cumulRegret.length;
            }
        }
        return strategy;
    }

    public float[] getAverageStrategy() {
        float normalizingSum = 0;
        float[] averageStrategy = new float[cumulStrategy.length];
        for (int i = 0; i < cumulStrategy.length; i++) {
            normalizingSum += cumulStrategy[i];
        }
        for (int i = 0; i < cumulStrategy.length; i++) {
            if (normalizingSum > 0) {
                averageStrategy[i] = cumulStrategy[i] / normalizingSum;
            } else {
                averageStrategy[i] = 1.0f / cumulStrategy.length;
            }
        }
        return averageStrategy;
    }
}
