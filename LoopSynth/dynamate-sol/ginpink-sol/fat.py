#!/usr/bin/python
import sys
print("🐍 Python path:", sys.path)
import os
import time
import argparse
import smtplib
import logging
from email.mime.text import MIMEText
from nondaemonicpool import NonDaemonicPool
from ginpink import read_methods, SolPinkTheory as PinkTheory
import traceback
from ginpink import SolidityMutator as CommonMutator

print("📆 fat.py is running!")

# Define mutation strategy functions
def strategy_basic(mutator):
    return mutator.mutations(n=1)

def strategy_post_pred(mutator):
    mutator.activate_post_predicates()
    return mutator.predicate_mutations(n=1)

def strategy_boolean(mutator):
    mutator.activate_theory_from_post(n=3)
    return mutator.predicate_mutations(n=0, more=1)

def strategy_scalar(mutator):
    mutator.activate_weakening_predicates()
    return mutator.scalar_mutations()

def strategy_aging(mutator):
    mutations = mutator.mutations_and_aging(n=1, n_age=1)
    unique = {}
    for m in mutations:
        if m is not None and hasattr(m, "text"):
            unique[m.text()] = m  # Use text as key to eliminate duplicates
    return list(unique.values())

MUTATION_STRATEGY_FUNCS = {
    "basic": strategy_basic,
    "post_pred": strategy_post_pred,
    "boolean": strategy_boolean,
    "scalar": strategy_scalar,
    "aging": strategy_aging,  # ✅ Add this
}

COMMAND_ORDER = ["basic", "post_pred", "boolean", "scalar", "aging"]
COMMAND_TIMEOUTS = {"basic": 20, "post_pred": 40, "boolean": 60, "scalar": 60}

EXTENSION = ".info"  # Updated for .info files

# Email notification utility
def send_email(subject, body, to="user@example.com"):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "no-reply@loop-inference.com"
    msg["To"] = to
    try:
        server = smtplib.SMTP("smtp.example.com", 587)
        server.starttls()
        server.login("user@example.com", "password")
        server.sendmail("no-reply@loop-inference.com", [to], msg.as_string())
        server.quit()
        print("📧 Email notification sent!")
    except Exception as e:
        print(f"⚠️ Email notification failed: {e}")

def process_batch(contract_batch, args, batch_id):
    print(f"🔁 Starting batch #{batch_id}: {contract_batch}")

    for contract in contract_batch:
        print(f"📦 Processing contract: {contract}")
        try:
            all_methods = read_methods(contract, args.theory_directory)
        except Exception as e:
            print(f"❌ Failed to read methods for {contract}: {e}")
            traceback.print_exc()  # Show full traceback for debugging
            continue

        if not all_methods:
            print(f"⚠️ No methods found in .info for {contract}")
            continue

        theory_path = os.path.join(args.theory_directory, "T" + contract + EXTENSION)
        theories = []
        if os.path.exists(theory_path):
            try:
                theory_obj = PinkTheory("T" + contract, [], [], pkg="")
                theories = [theory_obj]
            except Exception as e:
                print(f"❌ Failed to load theory for {contract}: {e}")
                traceback.print_exc()  # Optional but helpful here too

        for method_obj, posts, invs, pres in all_methods:
            try:
                print(f"▶️ Running inference on: {contract}.{method_obj.name}")

                mutator = CommonMutator(method_obj, theories, posts)
                print("📌 AST postconditions passed to mutator:")
                for p in posts:
                    try:
                        print(f" - {p.text()}")
                    except Exception as ex:
                        print(f" ⚠️ Cannot print post: {p}, error: {ex}")

                for strategy in COMMAND_ORDER:
                    if strategy in MUTATION_STRATEGY_FUNCS:
                        try:
                            start_time = time.time()
                            mutations = MUTATION_STRATEGY_FUNCS[strategy](mutator)
                            elapsed = time.time() - start_time
                            print(f"✅ Strategy {strategy} generated {len(mutations)} mutations in {elapsed:.2f}s")
                            for idx, m in enumerate(mutations, 1):
                                try:
                                    print(f"🧬 Mutation {idx} [{strategy}]: {m.text()}")
                                except Exception as ex:
                                    print(f"⚠️ Cannot print mutation {idx}: {ex}")

                        except Exception as e:
                            print(f"❌ Strategy {strategy} failed for {contract}.{method_obj.name}: {e}")
                    else:
                        print(f"⚠️ Strategy {strategy} not available (not implemented) for {contract}.{method_obj.name}")

                print(f"✅ Inference complete for {contract}.{method_obj.name}")

            except Exception as method_exc:
                print(f"🔥 Exception while processing {contract}.{method_obj.name}: {method_exc}")
                traceback.print_exc()  # Show full traceback for errors in method handling

    print(f"✅ Batch #{batch_id} finished.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='JML-based loop invariant inference from .info files')
    parser.add_argument('-P', '--processes', dest='P', type=int, default=4)
    parser.add_argument('--timeout', dest='timeout', type=int, default=300)
    parser.add_argument('--scalar', dest='scalar', action='store_true')
    parser.add_argument('--email', dest='email')
    parser.add_argument('--debug', dest='debug_file')
    parser.add_argument('--only', dest='only', type=int)
    parser.add_argument('--serialize', dest='serialize', action='store_true')
    parser.add_argument('--nonstrict', dest='strict', action='store_false')
    parser.add_argument('--fullnames', dest='fullyqualified', action='store_true')
    parser.add_argument('-q', '--explicitquantifiers', dest='print_all', action='store_true')
    parser.add_argument('-T', '--theory_directory', dest='theory_directory', default='.')
    parser.add_argument('contracts', nargs='+', metavar='INFO_FILE')
    args = parser.parse_args()

    if args.debug_file:
        logging.basicConfig(filename=args.debug_file, filemode='w', level=logging.DEBUG)

    contract_files = args.contracts
    N_procs = min(len(contract_files), args.P)
    batch_size = max(1, len(contract_files) // N_procs)
    batches = [contract_files[i:i + batch_size] for i in range(0, len(contract_files), batch_size)]

    print(f"🚀 Launching inference on {len(contract_files)} contracts using {N_procs} parallel processes.")

    pool = NonDaemonicPool(processes=N_procs)
    procs = [pool.apply_async(process_batch, args=(batch, args, i)) for i, batch in enumerate(batches)]

    for i, p in enumerate(procs):
        try:
            p.get()
        except Exception as e:
            print(f"❌ Error in batch #{i}: {e}")

    pool.close()
    pool.join()

    if args.email:
        send_email("Loop Inference: All Batches Complete", "All contract batches have completed.", args.email)
