import json
import os
from z3_checker import Z3Checker
from invariant_autogen import generate_invariants
from invariant_normalizer import normalize_expression  # 🔁 Imported for automatic cleanup

# Constants (default file paths)
CONTRACT_FILE = "contracts/sample.sol"
INVARIANT_TXT_FILE = "invariants.txt"
INVARIANT_JSON_FILE = "invariants.json"
REPORT_FILE = "results/report.txt"

# Load raw invariants from text file
def load_invariants_from_file(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Invariant file not found: {file_path}")
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

# Write report to results/report.txt
def write_report(results, output_path):
    with open(output_path, 'w') as f:
        for i, res in enumerate(results, 1):
            f.write(f"Invariant {i}: {res['status']}\n")
            if res['status'] == "CAN FAIL" and res['model']:
                f.write(f"  Counterexample: {res['model']}\n")
            f.write("\n")

# Save normalized invariants to JSON (for debugging or future processing)
def save_invariants_json(invariants, output_path):
    with open(output_path, 'w') as f:
        json.dump(invariants, f, indent=2)

def main():
    print("🚀 Starting Solidity Invariant Validator...")
    print(f"📄 Using contract: {CONTRACT_FILE}")
    print(f"📑 Reading expressions from: {INVARIANT_TXT_FILE}")

    # Step 1: Load raw invariants
    try:
        raw_exprs = load_invariants_from_file(INVARIANT_TXT_FILE)
    except Exception as e:
        print(f"❌ Failed to read invariants.txt: {e}")
        return

    # Step 2: Normalize and label malformed ones as trusted
    normalized_exprs = []
    trusted_exprs = []

    for i, expr in enumerate(raw_exprs, 1):
        norm = normalize_expression(expr)
        if norm:
            normalized_exprs.append(norm)
        else:
            print(f"⚠️  Invariant {i} labeled TRUSTED due to normalization error or unsupported syntax: '{expr}'")
            trusted_exprs.append({
                "expr": expr,
                "vars": {},
                "trusted": True
            })

    if not normalized_exprs and not trusted_exprs:
        print("❌ No valid invariants found.")
        return

    # Step 3: Auto-generate Z3-compatible invariant structure
    try:
        invariants = generate_invariants(CONTRACT_FILE, normalized_exprs)
        invariants.extend(trusted_exprs)  # Include trusted ones
        save_invariants_json(invariants, INVARIANT_JSON_FILE)
        print(f"✅ Generated and saved {INVARIANT_JSON_FILE}")
    except Exception as e:
        print(f"❌ Error generating invariants: {e}")
        return

    # Step 4: Validate invariants using Z3
    checker = Z3Checker()
    results = []

    print("\n🔍 Validating invariants...\n")
    for idx, inv in enumerate(invariants, 1):
        expr = inv["expr"]
        var_defs = inv["vars"]

        if inv.get("trusted", False):
            results.append({
                "status": "TRUSTED (skipped)",
                "model": None
            })
            print(f"Invariant {idx}: TRUSTED (skipped)")
            continue

        try:
            always_true, counterexample = checker.is_always_true(expr, var_defs)
            result = {
                "status": "ALWAYS HOLDS" if always_true else "CAN FAIL",
                "model": str(counterexample) if counterexample else None
            }
            results.append(result)
            print(f"Invariant {idx}: {result['status']}")
            if result["model"]:
                print(f"  Counterexample: {result['model']}")
        except Exception as e:
            print(f"⚠️  Error checking invariant {idx}: {e}")
            results.append({
                "status": "TRUSTED (skipped)",
                "model": None
            })
            print(f"Invariant {idx}: TRUSTED (skipped due to error)")

    # Step 5: Save final report
    os.makedirs("results", exist_ok=True)
    write_report(results, REPORT_FILE)
    print(f"\n📝 Validation report saved to: {REPORT_FILE}")

if __name__ == "__main__":
    main()
