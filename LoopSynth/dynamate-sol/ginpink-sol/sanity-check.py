#! /usr/bin/python

import argparse
import os
from solidity_exec import ExecutableSolidity
from reprocess import separator

# Define Solidity methods that require special treatment
methods_with_Integer = ['LoopInvariant.checkInvariant', 'LoopInvariant.mergeSort']


# --- ADDED: Sample read_methods function ---
def read_methods(contract_name):
    """
    Simulates reading method specs for a given contract.
    Replace this with real file I/O or AST parsing if needed.
    Returns list of tuples: (pm, postconditions, invariants, preconditions)
    """
    class PM:
        def __init__(self, name, enclosing, package):
            self.name = name
            self.enclosing = enclosing
            self.package = package

    class Enclosing:
        def __init__(self, name):
            self.name = name

    # Example hardcoded data for demonstration
    # In practice, load from JSON/YAML/AST or compile metadata
    dummy_methods = [
        (
            PM("checkInvariant", Enclosing("LoopInvariant"), "solidity"),
            [],  # postconditions
            [  # invariants
                "forall uint i; i >= 0 && i < len => arr[i] >= 0;",
                "val != 0 ==> Arrays.nonzero(arr, 0, len);"
            ],
            []  # preconditions
        )
    ]

    return dummy_methods if contract_name == "LoopInvariant" else []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check Solidity loop invariants')
    parser.add_argument('--tofile', dest='ext', action='store',
                        help='write results to separate files')
    parser.add_argument('-N', dest='niter', action='store', type=int, default=16,
                        help='number of expected iterations')
    parser.add_argument('contracts', nargs='+', metavar='C', action='append',
                        help='Solidity contract name(s)')
    args = parser.parse_args()

    contracts = args.contracts[0]
    methods = []

    for contract in contracts:
        methods += read_methods(contract)

    for pm, post, invs, pres in methods:
        method_name = pm.name
        contract_name = pm.enclosing.name
        package = pm.package
        expected_invariants = set()

        print(f"************ Checking {contract_name}.{method_name} ************")

        for i in invs:
            instr = i.strip().rstrip(';')
            ex = ExecutableSolidity(instr)
            ex.make_executable()
            extext = ex.get_text()

            isIntegerArray = f"{contract_name}.{method_name}" in methods_with_Integer
            qu = ExecutableSolidity(instr)
            qu.make_quantification(IntegerArrays=isIntegerArray, preconditions=True)
            qutext = qu.node.text() if hasattr(qu, 'node') else instr

            outline = extext + separator + qutext + '\n'
            expected_invariants.add(outline.strip())

        found = 0
        for n in range(1, args.niter + 1):
            filename = f"{package}.{contract_name}.{method_name}.iteration_{n}.mutations"
            if not os.path.exists(filename):
                continue
            with open(filename) as f:
                for line in f:
                    if line.strip() in expected_invariants:
                        print(f"{filename}: {line.strip()}")
                        found += 1

        if found != len(expected_invariants):
            print(f"--> Method {contract_name}.{method_name} found {found}, missing {len(expected_invariants) - found} invariants")
        print('\n')
