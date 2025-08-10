import os
import argparse
from z3 import *

# Constants
MARKER = "-----> All mutations follow"
SEPARATOR = "   <--exec|SOL-->  "
PACKAGE = "solidity"
CONTRACTS = ["LoopInvariantGenerator"]
FUNCTIONS = ["verifyLoopInvariant"]
ITERATION_MARKER = "iteration_"
ITERATIONS = range(1, 16 + 1)
EXTENSION = "mutations"

class CheckQuantifiedFormula:
    """Checks if quantified expressions in Solidity are correctly structured"""

    def __init__(self, expression):
        self.expression = expression.strip()
        self.is_well_formed = False

    def extract_variable_and_scope(self, quant_str):
        try:
            head = quant_str.strip()
            if not (head.startswith("forall") or head.startswith("exists")):
                return None, None

            # Example: forall uint i; i >= 0 && i < len => arr[i] >= 0
            # Split at ';' to get variable declaration and range
            parts = head.split(";")
            if len(parts) < 2:
                return None, None

            quant_var = parts[0].split()[-1].strip()
            range_and_cond = ";".join(parts[1:]).strip()
            return quant_var, range_and_cond
        except:
            return None, None

    def has_variable(self, expr, var):
        """Checks if variable appears in the expression"""
        return var in expr

    def check_validity(self):
        """Performs basic structural validation of quantified expressions"""
        if "forall" not in self.expression and "exists" not in self.expression:
            self.is_well_formed = True
            return

        try:
            # Assume format: forall uint i; i >= 0 && i < n => arr[i] >= 0
            quant_expr = self.expression.split("=>")
            if len(quant_expr) != 2:
                return

            quant_head, body = quant_expr[0].strip(), quant_expr[1].strip()
            var, range_expr = self.extract_variable_and_scope(quant_head)
            if not var or not range_expr:
                return

            # Check that the quantified variable appears both in range and body
            if not self.has_variable(range_expr, var) or not self.has_variable(body, var):
                return

            self.is_well_formed = True
        except:
            self.is_well_formed = False


def wellformed_quantifier(expression):
    """Wrapper for quantifier validation"""
    checker = CheckQuantifiedFormula(expression)
    checker.check_validity()
    return checker.is_well_formed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reprocess Solidity mutation files for loop invariants")
    parser.add_argument('--QTcheck', dest='QTcheck', action='store_true',
                        help="Only check validity of quantified expressions (default: %(default)s)")
    args = parser.parse_args()

    for contract in CONTRACTS:
        for function in FUNCTIONS:
            for i in ITERATIONS:
                iteration_label = ITERATION_MARKER + str(i)
                filename = f"{PACKAGE}.{contract}.{function}.{iteration_label}.{EXTENSION}"

                if not os.path.exists(filename):
                    continue

                with open(filename + ".new", "w") as outf:
                    with open(filename) as f:
                        content = False
                        for line in f:
                            if line.strip() == MARKER:
                                content = True
                                outf.write(line)
                                continue

                            if not content:
                                outf.write(line)
                                continue

                            if SEPARATOR not in line:
                                continue

                            predicate, quant_expr = line.strip().split(SEPARATOR)

                            if "solidity.theories.QT" in predicate:
                                if args.QTcheck and wellformed_quantifier(quant_expr):
                                    outf.write(predicate + SEPARATOR + quant_expr + '\n')
                                continue

                            if args.QTcheck:
                                outf.write(predicate + SEPARATOR + quant_expr + '\n')
                                continue

                            new_predicate = predicate.replace("solidity.theories.", "")

                            # Simple handling of \old, may expand later
                            executable_expr = quant_expr if "\\old" in quant_expr else new_predicate

                            # Logical check using Z3
                            try:
                                solver = Solver()
                                solver.add(eval(executable_expr))  # Use with caution
                                if solver.check() == sat:
                                    outf.write(new_predicate + SEPARATOR + executable_expr + '\n')
                            except Exception as e:
                                pass  # Skip invalid expressions
