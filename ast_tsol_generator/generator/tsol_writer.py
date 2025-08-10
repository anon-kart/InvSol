import os

def dummy_value(sol_type):
    """
    Returns a dummy Solidity value for a given type.
    (Unused in the new fuzz version but kept for possible fallback.)
    """
    if sol_type.startswith("uint"):
        return "100"
    if sol_type == "address":
        return "address(this)"
    if sol_type == "bool":
        return "true"
    if sol_type == "string":
        return '"example"'
    return "0"

def write_test_file(contract_name, function_signatures, input_sol_path, output_path):
    """
    Writes a .t.sol test file using Foundry-compatible syntax.
    - Imports forge-std/Test.sol
    - Imports the input contract
    - Generates fuzzable test functions with parameter lists, vm.assume guards, and log_named_* emits
    - Adds a special combined Deposit+Withdraw sequential test if both exist
    """
    test_contract_name = f"{contract_name}_Test"
    relative_contract_path = os.path.relpath(input_sol_path, os.path.dirname(output_path))

    with open(output_path, "w") as f:
        # Header
        f.write('// SPDX-License-Identifier: UNLICENSED\n')
        f.write('pragma solidity ^0.8.13;\n\n')
        f.write('import "forge-std/Test.sol";\n')
        f.write(f'import "../{relative_contract_path}";\n\n')

        # Test contract
        f.write(f'contract {test_contract_name} is Test {{\n')
        f.write(f'    {contract_name} contractInstance;\n\n')

        # Setup function
        f.write('    function setUp() public {\n')
        f.write(f'        contractInstance = new {contract_name}();\n')
        f.write('    }\n\n')

        # Fuzzable test functions for *each* public function
        for i, (func_name, param_types) in enumerate(function_signatures):
            fuzz_params = [f"{sol_type} arg{j}" for j, sol_type in enumerate(param_types)]
            fuzz_params_str = ", ".join(fuzz_params)

            f.write(f'    function testFuzz_{func_name}_{i}({fuzz_params_str}) public {{\n')

            # Add vm.assume guards for uints
            for j, sol_type in enumerate(param_types):
                if sol_type.startswith("uint"):
                    f.write(f'        vm.assume(arg{j} < 1e18);\n')

            # Emit log_named_* lines for all args
            for j, sol_type in enumerate(param_types):
                if sol_type.startswith("uint"):
                    f.write(f'        emit log_named_uint("arg{j}", arg{j});\n')
                elif sol_type == "address":
                    f.write(f'        emit log_named_address("arg{j}", arg{j});\n')
                elif sol_type == "bool":
                    f.write(f'        emit log_named_bool("arg{j}", arg{j});\n')
                elif sol_type == "string":
                    f.write(f'        emit log_named_string("arg{j}", arg{j});\n')

            call_args = ", ".join(f"arg{j}" for j in range(len(param_types)))
            f.write(f'        contractInstance.{func_name}({call_args});\n')
            f.write('    }\n\n')

        # Check if BOTH deposit and withdraw exist ➜ add combined flow
        has_deposit = any(name == "deposit" for name, _ in function_signatures)
        has_withdraw = any(name == "withdraw" for name, _ in function_signatures)

        if has_deposit and has_withdraw:
            f.write('    function testFuzz_DepositWithdraw(address user, uint256 depositAmount, uint256 withdrawAmount) public {\n')
            f.write('        vm.assume(depositAmount < 1e18);\n')
            f.write('        vm.assume(withdrawAmount <= depositAmount);\n')
            f.write('        emit log_named_address("user", user);\n')
            f.write('        emit log_named_uint("depositAmount", depositAmount);\n')
            f.write('        emit log_named_uint("withdrawAmount", withdrawAmount);\n')
            f.write('        vm.startPrank(user);\n')
            f.write('        contractInstance.deposit(depositAmount);\n')
            f.write('        contractInstance.withdraw(withdrawAmount);\n')
            f.write('        vm.stopPrank();\n')
            f.write('        uint256 finalBalance = contractInstance.balanceOf(user);\n')
            f.write('        assertEq(finalBalance, depositAmount - withdrawAmount);\n')
            f.write('    }\n\n')

        f.write('}\n')
