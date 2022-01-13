from trainer import Trainer
from state import get_root_state

if __name__ == "__main__":
    trainer = Trainer()
    for t in range(5000):
        if t % 1000 == 0:
            print('Iteration', t)
        for traverser in [0, 1]:  # SB, BB
            trainer.cfr(get_root_state(), traverser, t)
    # print(trainer)

# TODO: threading, thresholds for recursively updating strategies + pruning + discounting, saving to disk
