// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../../contracts/Bank.sol";

contract Bank_Test is Test {
    Bank contractInstance;

    function setUp() public {
        contractInstance = new Bank();
    }

    function testFuzz_deposit_0(uint256 arg0) public {
        vm.assume(arg0 < 1e18);
        emit log_named_uint("arg0", arg0);
        contractInstance.deposit(arg0);
    }

    function testFuzz_withdraw_1(uint256 arg0) public {
        vm.assume(arg0 < 1e18);
        emit log_named_uint("arg0", arg0);
        contractInstance.withdraw(arg0);
    }

    function testFuzz_balanceOf_2(address arg0) public {
        emit log_named_address("arg0", arg0);
        contractInstance.balanceOf(arg0);
    }

    function testFuzz_DepositWithdraw(address user, uint256 depositAmount, uint256 withdrawAmount) public {
        vm.assume(depositAmount < 1e18);
        vm.assume(withdrawAmount <= depositAmount);
        emit log_named_address("user", user);
        emit log_named_uint("depositAmount", depositAmount);
        emit log_named_uint("withdrawAmount", withdrawAmount);
        vm.startPrank(user);
        contractInstance.deposit(depositAmount);
        contractInstance.withdraw(withdrawAmount);
        vm.stopPrank();
        uint256 finalBalance = contractInstance.balanceOf(user);
        assertEq(finalBalance, depositAmount - withdrawAmount);
    }

}
