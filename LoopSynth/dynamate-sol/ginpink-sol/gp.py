#!/usr/bin/python
import os
import sys
import time
import argparse
import logging
import pickle
import re
import multiprocessing

from solidity_parser_util import (
    parse_solidity,
    extract_solidity_methods,
    extract_require_statements,
    extract_assert_statements,
)
from ginpink import *

SOLIDITY_CONTRACTS_DIR = "/home/kartik/dynamate-sol/theories/"
EXTENSION = ".sol"

class PlainPrinter:
    def __init__(self, name, iteration):
        self.name = name
        self.iteration = iteration

    def printout(self, message):
        print(message)

    def done(self):
        pass

class FilePrinter(PlainPrinter):
    def __init__(self, name, iteration):
        super().__init__(name, iteration)
        version = 1
        while True:
            filename = f"{self.name}.iteration_{self.iteration}.v{version}.txt"
            if not os.path.exists(filename):
                self.file = open(filename, "w")
                break
            version += 1

    def printout(self, message):
        self.file.write(message + '\n')

    def done(self):
        self.file.close()

class MutationTracker:
    def __init__(self, method_name, expected_invariants):
        self.method_name = method_name
        self.iterations = []
        self.all_mutations = set()
        self.expected_invariants = set(expected_invariants)
        self.cur_iteration = 0
        self.commands = []
        self.generated = []
        self.outcome = []
        self.times = []
        self.found_invariants = []

    def new_iteration(self, commands):
        self.cur_iteration += 1
        self.iterations.append(set())
        self.commands.append(commands)
        self.outcome.append(None)
        self.found_invariants.append(set())
        self.times.append(None)
        self.generated.append(None)

    def new_mutations(self, mutations, generated):
        news = set(mutations) - self.all_mutations
        self.all_mutations.update(news)
        self.iterations[self.cur_iteration - 1] = news
        self.outcome[self.cur_iteration - 1] = len(news)
        self.found_invariants[self.cur_iteration - 1] = set(
            [n for n in news if n in self.expected_invariants]
        )
        self.generated[self.cur_iteration - 1] = generated
        return news

    def has_found_all(self):
        return self.expected_invariants.issubset(self.all_mutations)

    def save_progress(self, filename):
        with open(filename, "wb") as f:
            pickle.dump(self, f)

def executable_forms(mutations, debug=False, strict=False):
    exec_mutations = []
    for mutation in mutations:
        if debug:
            logging.debug(f"Computing executable form of: {mutation}")
        if not re.match(r"^[a-zA-Z0-9_()\s><=!&|+\-/*]+$", mutation):
            print(f"[FILTERED - bad chars] {mutation}")
            continue
        if strict and re.match(r"^\s*(true|false|x\s*==\s*x)\s*$", mutation):
            print(f"[FILTERED - strict rule] {mutation}")
            continue
        exec_mutations.append(mutation)
    return exec_mutations

def process_commandsequence(command_sequence, mutator, debug=False):
    mutations = []
    print(f"[CHILD DEBUG] Starting command sequence: {command_sequence}")
    
    for cmd in command_sequence:
        if hasattr(mutator, cmd):
            method = getattr(mutator, cmd)
            print(f"[CHILD DEBUG] Executing mutator method: {cmd}")
            try:
                generated = method()
                print(f"[CHILD DEBUG] Method '{cmd}' generated {len(generated)} mutations.")
                mutations.extend(generated)
                for m in generated:
                    print(f"[CHILD RAW MUTATION] {m}")
            except Exception as e:
                print(f"[CHILD ERROR] Exception during '{cmd}': {e}")
        else:
            print(f"[CHILD WARNING] Mutator has no method named '{cmd}'")
    
    print(f"[CHILD RETURNING] Total mutations: {len(mutations)}")
    return mutations

def process_method(method_name, postconditions, invariants, theories,
                   debug=False, timeout=60, print_to_file=True, special=None):
    tracker = MutationTracker(method_name, invariants)
    printer = FilePrinter(method_name, tracker.cur_iteration) if print_to_file else PlainPrinter(method_name, tracker.cur_iteration)

    command_sequences = special if special else [["mutations"]]

    for commands in command_sequences:
        if tracker.has_found_all():
            break
        tracker.new_iteration("; ".join(commands))
        mutator = SolidityMutator(method_name, theories)

        # 🔁 Start the subprocess for mutation generation
        pool = multiprocessing.Pool(processes=1)
        result = pool.apply_async(process_commandsequence, args=(commands, mutator, debug))

        try:
            mutations = result.get(timeout=timeout)  # ⏳ Wait for result from subprocess
            if mutations is None:
                print("[DEBUG] Subprocess returned None.")
            elif isinstance(mutations, list):
                print(f"[DEBUG] Subprocess returned list of {len(mutations)} items.")
            else:
                print(f"[DEBUG] Subprocess returned: {type(mutations)} → {mutations}")

            print(f"[DEBUG] Received {len(mutations)} mutations from subprocess")  # 🔍 Confirm we got something
        except multiprocessing.TimeoutError:
            pool.terminate()
            mutations = None
            print("[ERROR] Subprocess timed out — no mutations returned.")
        finally:
            pool.close()
            pool.join()

        if mutations:
            mutations = set(mutations)

            # 📤 Log raw mutations before filtering
            for m in mutations:
                printer.printout(f"[RAW MUTATION] {m}")
                print(f"[RAW MUTATION] {m}")

            # ✅ Filter executable forms (disable strict for debugging)
            executable_mutations = executable_forms(mutations, debug=debug, strict=False)

            # 🧹 Log filtered-out mutations inside executable_forms() directly
            tracker.new_mutations(executable_mutations, len(mutations))

            # 🟢 Log executable (kept) mutations
            for m in executable_mutations:
                printer.printout(f"[MUTATION] {m}")
                print(f"[MUTATION] {m}")

            # 📈 Summary log
            printer.printout(f"✅ Strategy {'; '.join(commands)} generated {len(executable_mutations)} mutations.")
        else:
            printer.printout("⚠️ No mutations generated (timeout or empty result).")
            print("⚠️ No mutations returned from subprocess.")

        # 💾 Save tracker progress
        tracker.save_progress(f"{method_name}.pkl")

    printer.done()
    return tracker

def get_methods_and_theories(contract_names, theory_dir):
    methods = []
    theories = {}

    for fname in os.listdir(theory_dir):
        if fname.startswith("T") and fname.endswith(".sol"):
            contract_name = fname[:-4]
            try:
                theory_obj = read_contract(contract_name, theory_dir)
                theories[contract_name] = theory_obj
            except Exception as e:
                print(f"❌ Failed to read theory file {fname}: {e}")

    for contract in contract_names:
        contract_path = os.path.join(SOLIDITY_CONTRACTS_DIR, contract + EXTENSION)
        if not os.path.exists(contract_path):
            continue

        with open(contract_path, "r") as f:
            contract_code = f.read()

        try:
            ast_tree = parse_solidity(contract_code)
        except Exception as e:
            print(f"❌ Failed to parse {contract}: {e}")
            continue

        extracted = extract_solidity_methods(ast_tree)

        for contract_name, funcs in extracted.items():
            for fname in funcs:
                theory_preds = []
                if contract_name in theories:
                    try:
                        theory_preds.extend(theories[contract_name].get_bools())
                    except Exception as e:
                        print(f"❌ Error extracting predicates: {e}")
                methods.append((fname, contract_name, theory_preds))

    return methods, theories

def process_with_commands(contract_names, theory_dir, method_only=None, printall=False,
                          fullyqualified=False, expandquant=False, debug=False, timeout=60,
                          only=0, serialize=False, skip=False, special=None, strict=True):
    methods, theories = get_methods_and_theories(contract_names, theory_dir)
    if method_only:
        methods = [m for m in methods if m[0] == method_only]
        if not methods:
            return None

    results = []

    for function_name, contract_name, function_theories in methods:
        contract_path = os.path.join(SOLIDITY_CONTRACTS_DIR, contract_name + EXTENSION)
        if not os.path.exists(contract_path):
            continue

        with open(contract_path, "r") as f:
            contract_code = f.read()

        try:
            ast_tree = parse_solidity(contract_code)
        except Exception as e:
            print(f"❌ Failed to parse {contract_name}: {e}")
            continue

        func_node = None
        for child in ast_tree.get('children', []):
            if child.get('type') == 'ContractDefinition':
                for sub in child.get('nodes', []) or child.get('subNodes', []):
                    if sub.get('type') == 'FunctionDefinition' and sub.get('name') == function_name:
                        func_node = sub
                        break
            if func_node:
                break

        if not func_node:
            continue

        postconditions = extract_assert_statements(contract_code, function_name)
        preconditions = extract_require_statements(contract_code, function_name)

        tracker = process_method(
            function_name,
            postconditions + preconditions,  # Invariants include both pre and post for now
            function_theories,
            theories,
            debug=debug,
            timeout=timeout,
            special=special
        )
        results.append(tracker)

    return results if results else None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate mutations for Solidity smart contracts.')
    parser.add_argument('-T', dest='theory_directory', default='.')
    parser.add_argument('-m', dest='method_name')
    parser.add_argument('--tofile', dest='ext')
    parser.add_argument('--command', dest='cmd')
    parser.add_argument('--fullnames', dest='fullyqualified', action='store_true')
    parser.add_argument('-q', '--explicitquantifiers', dest='explicitquant', action='store_true')
    parser.add_argument('-a', '--all', dest='print_all', action='store_true')
    parser.add_argument('--serialize', dest='serialize', action='store_true')
    parser.add_argument('--only', dest='only', type=int)
    parser.add_argument('--to', '--timeout', dest='timeout', type=int)
    parser.add_argument('--nonstrict', dest='strict', action='store_false')
    parser.add_argument('--debug', dest='debug_file')
    parser.add_argument('classes', nargs='+', metavar='C')

    args = parser.parse_args()
    debug = args.debug_file is not None
    if debug:
        logging.basicConfig(filename=args.debug_file, filemode='w', level=logging.DEBUG)

    special_commands = None
    if args.cmd:
        special_commands = [[c.strip() for c in args.cmd.split(';')]]

    process_with_commands(
        contract_names=args.classes,
        theory_dir=args.theory_directory,
        method_only=args.method_name,
        printall=args.print_all,
        fullyqualified=args.fullyqualified,
        expandquant=args.explicitquant,
        debug=debug,
        timeout=args.timeout or 60,
        only=args.only or 0,
        serialize=args.serialize,
        strict=args.strict,
        special=special_commands
    )
