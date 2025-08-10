import subprocess
import json

def get_ast(sol_file_path):
    """
    Calls solc to get the AST (compact JSON) for a Solidity file.
    Extracts and returns only the JSON part from the output.
    """
    try:
        result = subprocess.run(
            ["solc", "--ast-compact-json", sol_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        # Combine stdout and stderr to handle all solc output
        combined_output = result.stdout + result.stderr

        # Locate the actual JSON start
        json_start = combined_output.find('{')
        if json_start == -1:
            raise RuntimeError("JSON output not found in solc output.")
        
        ast_raw = combined_output[json_start:].strip()
        return json.loads(ast_raw)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"solc failed: {e.stderr}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to decode JSON from solc output: {e}")


def extract_contract_info(ast):
    """
    Traverses the AST and extracts:
    - The first contract name
    - A list of (function_name, [param_types]) for public, implemented functions
    Returns (contract_name, [(function_name, [param_types])])
    """
    contract_name = None
    function_signatures = []

    try:
        # Case 1: Flat top-level AST (not wrapped in 'sources')
        if "nodeType" in ast and ast["nodeType"] == "SourceUnit":
            nodes = ast.get("nodes", [])
        # Case 2: Wrapped under 'sources' (standard JSON input)
        elif "sources" in ast:
            nodes = []
            for source_data in ast["sources"].values():
                nodes.extend(source_data.get("ast", {}).get("nodes", []))
        else:
            raise RuntimeError("Unrecognized AST format")

        for node in nodes:
            if node.get("nodeType") == "ContractDefinition":
                contract_name = node.get("name")
                for item in node.get("nodes", []):
                    if (
                        item.get("nodeType") == "FunctionDefinition"
                        and item.get("visibility") == "public"
                        and item.get("implemented") is True
                    ):
                        fname = item.get("name")
                        param_types = []
                        # Extract parameter types
                        params = item.get("parameters", {}).get("parameters", [])
                        for param in params:
                            type_str = param.get("typeDescriptions", {}).get("typeString", "UNKNOWN")
                            param_types.append(type_str)
                        if fname:
                            function_signatures.append( (fname, param_types) )
                break  # Only parse the first contract

    except Exception as e:
        raise RuntimeError(f"Failed to parse AST structure: {e}")

    if not contract_name:
        raise ValueError("No contract found in AST.")

    return contract_name, function_signatures
