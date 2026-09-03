#!/usr/bin/python

import os
import sys
import pickle
import argparse

logext = '.log'
datext = '.dat'

def read_dats(contract_name, print_all):
    """
    Reads stored Solidity loop invariants from serialized `.dat` files.
    """
    n = 1
    fn = f"{contract_name}.iteration_{n}{datext}"
    while os.path.exists(fn):
        n += 1
        fn = f"{contract_name}.iteration_{n}{datext}"

    # Last valid iteration
    n -= 1
    fn = f"{contract_name}.iteration_{n}{datext}"
    if not os.path.exists(fn):
        print(f"❌ No stored iteration for contract: {contract_name}")
        sys.exit(0)

    # Load stored loop invariants
    with open(fn, 'rb') as f:
        mw = pickle.load(f)

    print(f"\n🔍 Loop Invariant Analysis for Solidity Contract: {contract_name}")
    print("------------------------------------------------------------")
    print(mw)

    if print_all:
        print("\n🔹 -----> All inferred loop invariants per iteration:")
        if "mutations" in mw:
            for i, iteration_mutations in enumerate(mw["mutations"]):
                print(f"\n🔹 -----> Iteration {i + 1}:")
                for mutation in iteration_mutations:
                    exec_text = mutation[0].text() if hasattr(mutation[0], 'text') else str(mutation[0])
                    spec_text = mutation[1].text() if hasattr(mutation[1], 'text') else str(mutation[1])
                    print(f"  {exec_text}   <--exec|spec-->   {spec_text}")
        elif "inferred_invariants" in mw:
            for i in range(n):
                print(f"\n🔹 -----> Iteration {i + 1}:")
                for inv in mw["inferred_invariants"]:
                    print(f"  - {inv}")
        else:
            print("⚠️ No recognizable invariant data found.")

def table_up(contract_name, ext):
    """
    Formats Solidity loop invariant results into CSV-style output.
    """
    fn = contract_name + ext
    if not os.path.exists(fn):
        print(f"❌ No result file with name: {fn}")
        sys.exit(0)

    rows = []
    with open(fn) as f:
        for line in f.readlines():
            cnt = line.strip().split(' ')
            if line.startswith("-----> Generated"):
                rows.append((cnt[-1], cnt[10]))  # mutations, validated
            elif line.startswith("No mutations generated within a timeout of"):
                rows.append((cnt[-2], "0"))
            elif line.startswith("No mutations returned"):
                rows.append(("0", "0"))

    res = '; '.join([' ; '.join(row + (" ",)) for row in rows])
    return contract_name + ' ; ' + res

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Analyze Solidity loop invariants from stored data.")
    parser.add_argument('C', nargs=1, metavar='C', action='store',
                        help="Solidity contract name to be processed (reading `.dat` files)")
    parser.add_argument('-t', '--table', dest='table', action='store',
                        help="Print results from .%(dest)s file in CSV format")
    parser.add_argument('-a', '--all', dest='print_all', action='store_true',
                        help="Print all inferred invariants from each iteration")
    args = parser.parse_args()

    contract_name = args.C[0]
    if not args.table:
        read_dats(contract_name, args.print_all)
    else:
        print(table_up(contract_name, '.' + args.table))

