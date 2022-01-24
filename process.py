import pickle

new = {}
for bucket in range(-128, 170):
    for rd in ['P', 'F', 'T', 'R']:
        new[rd + str(bucket)] = {}
with open('avgstrategy.pickle', 'rb') as f:
    strategy_map = pickle.load(f)
    for s in strategy_map:
        idx = -1
        while s[idx] not in {'P', 'F', 'T', 'R'}:
            idx -= 1
        new[s[idx:]][s] = strategy_map[s]

for entry in new:
    if len(new[entry]) > 0:
        with open(f'avgstrategy/{entry}.pickle', 'wb') as f:
            pickle.dump(new[entry], f, protocol=4)
