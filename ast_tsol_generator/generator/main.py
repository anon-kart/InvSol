from .ast_parser import get_ast, extract_contract_info
from .tsol_writer import write_test_file

def process_contract(input_sol_path, output_tsol_path):
    """
    Orchestrates the whole pipeline:
    1. Extracts AST
    2. Parses contract and function info
    3. Writes the .t.sol test file
    """
    ast = get_ast(input_sol_path)
    contract_name, function_names = extract_contract_info(ast)
    write_test_file(contract_name, function_names, input_sol_path, output_tsol_path)
