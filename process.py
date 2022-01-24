import pickle

new = {}
for bucket in range(-128, 170):
    for rd in ['P', 'F', 'T', 'R']:
        new[rd + str(bucket)] = {}

# with open('avgstrategy.pickle', 'rb') as f:
#     strategy_map = pickle.load(f)
#     for s in strategy_map:
#         idx = -1
#         while s[idx] not in {'P', 'F', 'T', 'R'}:
#             idx -= 1
#         new[s[idx:]][s] = strategy_map[s]

with open('nodeMap.txt') as f:
    lines = f.readlines()
    for line in lines:
        text = line.split(":")
        infoset_str = text[0]
        avg_strategy = eval(text[1].strip())
        idx = -1
        while infoset_str[idx] not in {'P', 'F', 'T', 'R'}:
            idx -= 1
        new[infoset_str[idx:]][infoset_str] = avg_strategy

for entry in new:
    if len(new[entry]) > 0:
        with open(f'avgstrategy/{entry}.pickle', 'wb') as f:
            pickle.dump(new[entry], f, protocol=4)
