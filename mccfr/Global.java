package mccfr;

import java.io.*;
import java.util.concurrent.*;


public class Global {
    public static HandIndexer indexer2 = new HandIndexer(new int[] {2});
    public static HandIndexer indexer23 = new HandIndexer(new int[] {2, 3});
    public static HandIndexer indexer24 = new HandIndexer(new int[] {2, 4});
    public static HandIndexer indexer25 = new HandIndexer(new int[] {2, 5});

    public static byte[] flopClusters;
    public static byte[] turnClusters;
    public static byte[] riverClusters;

    public static final int NOF_THREADS = 1;

    public static ConcurrentHashMap<String, Infoset> nodeMap = new ConcurrentHashMap<String, Infoset>(1000000, 0.75f, NOF_THREADS);

    public static void init() throws Exception {
        ObjectInputStream inputStream1 = new ObjectInputStream(new FileInputStream("flop_clusters"));
        flopClusters = (byte[])inputStream1.readObject();
        inputStream1.close();
        ObjectInputStream inputStream2 = new ObjectInputStream(new FileInputStream("turn_clusters"));
        turnClusters = (byte[])inputStream2.readObject();
        inputStream2.close();
        ObjectInputStream inputStream3 = new ObjectInputStream(new FileInputStream("river_clusters"));
        riverClusters = (byte[])inputStream3.readObject();
        inputStream3.close();
    }
}
