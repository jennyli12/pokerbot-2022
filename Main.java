import poker.*;
import mccfr.*;

import java.util.stream.IntStream;
import java.util.Random;
import java.util.concurrent.atomic.AtomicLong;
import java.io.*;
import java.util.Arrays;

class Main {
    public static void main(String[] args) throws Exception {
        Global.init();
        long strategyInterval = Math.max(1, 1000 / Global.NOF_THREADS);
        long pruneThreshold = 20000000 / Global.NOF_THREADS;
        long lcfrThreshold = 20000000 / Global.NOF_THREADS;
        long discountInterval = 1000000 / Global.NOF_THREADS;
        long saveToDiskInterval = 1000000 / Global.NOF_THREADS;
        long testGamesInterval = 100000 / Global.NOF_THREADS;

        AtomicLong sharedLoopCounter = new AtomicLong(0);
        long startTime = System.currentTimeMillis();
        
        Trainer trainer = new Trainer();
        for (int t = 1; ; t++) {
            if (t % 1000 == 0) {
                System.out.println(t);
                System.out.println("Iterations per second " + 1000 * t / (System.currentTimeMillis() - startTime));
                System.out.println("Minutes running " + (System.currentTimeMillis() - startTime) / 60000);
                System.out.println("Infosets " + Global.nodeMap.size());
            } 
            if (t % testGamesInterval == 0) {
                trainer.printStartingHandsChart();
            }
            for (int traverser = 0; traverser < 2; traverser++) {
                if (t % strategyInterval == 0) {
                    trainer.updateStrategy(new RoundState(), traverser);
                }
                if (t > pruneThreshold && new Random().nextFloat() < 0.95) {
                    trainer.cfr(new RoundState(), traverser, true);
                } else {
                    trainer.cfr(new RoundState(), traverser, false);
                }
            }
            if (t % saveToDiskInterval == 0) {
                saveToFile();
            }
            if (t < lcfrThreshold && t % discountInterval == 0) {
                float d = ((float) t / discountInterval) / ((float) t / discountInterval + 1);
                trainer.discountInfosets(d);
            }
        }

        // IntStream.range(0, Global.NOF_THREADS).parallel().forEach(index -> {
        //     Trainer trainer = new Trainer();
        //     for (int t = 1; ; t++) {
        //         if (t % 1000 == 0) {
        //             sharedLoopCounter.addAndGet(1000);
        //             System.out.println("Training iterations " + t);
        //         }
        //         if (t % testGamesInterval == 0 && index == 0) {
        //             trainer.printStartingHandsChart();
        //             System.out.println("Iterations per second " + 1000 * sharedLoopCounter.longValue() / (System.currentTimeMillis() - startTime));
        //             System.out.println("Minutes running " + 1000 * (System.currentTimeMillis() - startTime) / 60);
        //             System.out.println("Infosets " + Global.nodeMap.size());
        //         }
        //         for (int traverser = 0; traverser < 2; traverser++) {
        //             if (t % strategyInterval == 0 && index == 0) {
        //                 trainer.updateStrategy(new RoundState(), traverser);
        //             }
        //             if (t > pruneThreshold && new Random().nextFloat() < 0.95) {
        //                 trainer.cfr(new RoundState(), traverser, true);
        //             } else {
        //                 trainer.cfr(new RoundState(), traverser, false);
        //             }
        //         }
        //         if (t % saveToDiskInterval == 0 && index == 0) {
        //             // saveToFile();
        //         }
        //         if (t < lcfrThreshold && t % discountInterval == 0 && index == 0) {
        //             float d = ((float) t / discountInterval) / ((float) t / discountInterval + 1);
        //             trainer.discountInfosets(d);
        //         }
        //     }
        // });

        // for (String key : Global.nodeMap.keySet()) {
        //     if (key.charAt(0) == 'P') {
        //         System.out.println(key + ": " + Arrays.toString(Global.nodeMap.get(key).getAverageStrategy()));
        //     }
        // }
    }
    public static void saveToFile() throws Exception {
        ObjectOutputStream outputStream = new ObjectOutputStream(new FileOutputStream("nodeMap"));
        outputStream.writeObject(Global.nodeMap);
        outputStream.close();
    }
}