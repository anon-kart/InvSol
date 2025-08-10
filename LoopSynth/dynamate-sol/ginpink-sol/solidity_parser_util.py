from solidity_parser import parser

# Optional: Still useful for loop detection and function enumeration
def parse_solidity(contract_code):
    """
    Parses Solidity code and returns an AST representation.
    """
    return parser.parse(contract_code)


def extract_solidity_methods(ast_tree):
    """
    Extracts functions from a Solidity contract and detects those containing loops.
    Returns: dict of {contract_name: [function_names_with_loops]}
    """
    loop_functions = {}

    for node in ast_tree.get('children', []):
        if node.get('type') == 'ContractDefinition':
            contract_name = node['name']
            loop_functions[contract_name] = []

            for func in node.get('subNodes', []):
                if func.get('type') == 'FunctionDefinition' and 'body' in func:
                    body = func['body']
                    if 'statements' in body:
                        if any(stmt.get('type') in ['WhileStatement', 'ForStatement', 'DoWhileStatement']
                               for stmt in body.get('statements', [])):
                            loop_functions[contract_name].append(func.get('name'))

    return loop_functions


# ⚠️ The following are deprecated when using `.info` files
# But to prevent import errors, we’ll keep them and mark as unused

def extract_require_statements(*args, **kwargs):
    """
    Deprecated: You should extract preconditions from `.info` files using read_methods().
    """
    raise NotImplementedError("extract_require_statements() is no longer used. Use read_methods() instead.")


def extract_assert_statements(*args, **kwargs):
    """
    Deprecated: You should extract postconditions from `.info` files using read_methods().
    """
    raise NotImplementedError("extract_assert_statements() is no longer used. Use read_methods() instead.")


# 🛠️ Optional: May still be used for introspection or stats
def extract_function_details(ast_tree):
    """
    Extracts basic function structure for possible reporting/stats. Not used for pre/post/inv.
    """
    functions = {}

    for node in ast_tree.get('children', []):
        if node.get('type') == 'ContractDefinition':
            contract_name = node['name']
            functions[contract_name] = []

            for func in node.get('subNodes', []):
                if func.get('type') == 'FunctionDefinition':
                    name = func.get('name', '')
                    loops = False
                    if 'body' in func and 'statements' in func['body']:
                        loops = any(stmt.get('type') in ['WhileStatement', 'ForStatement', 'DoWhileStatement']
                                    for stmt in func['body']['statements'])
                    functions[contract_name].append({
                        "name": name,
                        "preconditions": [],  # intentionally empty (replaced by .info files)
                        "postconditions": [],
                        "loops": loops
                    })
    return functions
