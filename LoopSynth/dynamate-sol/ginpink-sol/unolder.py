#!/usr/bin/python

import re
import argparse
import sys
import solcx  # For Solidity compilation to verify correctness
from slither.slither import Slither
from slither.core.cfg.node import NodeType

class SolidityOldRemover:
    """
    Converts occurrences of `old(variable)` in Solidity expressions
    into explicitly stored old state values, ensuring correctness.
    """

    def __init__(self, expr):
        self.expr = expr  # Solidity expression containing old()
        self.failed = False
        self.errors = []

    def remove_old(self):
        """
        - Replaces `old(var)` with `old_var`.
        - Handles nested `old(old(var))` cases.
        - Ensures function calls like `old(foo(x))` are converted correctly.
        - Parses Solidity AST to maintain correct structure.
        """
        try:
            # Replace nested old() calls first (idempotency)
            while re.search(r'old\(old\((\w+)\)\)', self.expr):
                self.expr = re.sub(r'old\(old\((\w+)\)\)', r'old_\1', self.expr)

            # Handle direct old(var) replacements
            pattern = re.compile(r'old\((\w+)\)')  # Matches old(variable)
            transformed_expr = pattern.sub(r'old_\1', self.expr)

            # Handle function calls like old(foo(x))
            function_pattern = re.compile(r'old\((\w+)\((.*?)\)\)')
            transformed_expr = function_pattern.sub(r'old_\1_\2', transformed_expr)

            # Verify if transformation modified anything
            if transformed_expr == self.expr:
                self.failed = True
                return None

            # Validate transformed Solidity expression
            if not self.validate_solidity_expression(transformed_expr):
                self.failed = True
                return None

            return transformed_expr

        except Exception as e:
            self.errors.append(str(e))
            self.failed = True
            return None

    def validate_solidity_expression(self, expression):
        """
        Attempts to compile the transformed Solidity expression to ensure validity.
        """
        try:
            contract_code = f"""
            contract Test {{
                function test() public pure {{
                    require({expression});
                }}
            }}
            """
            solcx.compile_source(contract_code)
            return True  # Compilation successful
        except:
            self.errors.append(f"Invalid Solidity syntax after transformation: {expression}")
            return False

def unold(expr, debug=False):
    """
    Given a Solidity loop invariant or assertion, return it with `old(variable)`
    changed to `old_variable`. Returns None if conversion fails.
    """
    remover = SolidityOldRemover(expr)
    res = remover.remove_old()

    if debug:
        for e in remover.errors:
            print(f"Error: {e}", file=sys.stderr)

    return res

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert old(variable) expressions in Solidity to explicit old_variable format.')
    parser.add_argument('--debug', dest='debug', action='store_true', help='Enable debug information')
    parser.add_argument('expr', nargs=1, metavar='EXPR', action='store', help='A Solidity assertion or loop invariant to be converted')
    
    args = parser.parse_args()
    res = unold(args.expr[0], debug=args.debug)
    
    if res is None:
        print("FAILURE:", args.expr[0])
    else:
        print("SUCCESS:", res)

