// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract RoleRegistry {
    address public admin;
    mapping(address => bool) public operators;
    mapping(address => bool) public auditors;
    address[] public members;
    uint256 public operatorCount;

    event MembersPurged(uint256 removed);

    modifier onlyAdmin() {
        require(msg.sender == admin, "not-admin");
        _;
    }

    modifier onlyOperator() {
        require(operators[msg.sender], "not-operator");
        _;
    }

    constructor() {
        admin = msg.sender;
        operators[msg.sender] = true;
        operatorCount = 1;
    }

    function grantOperator(address account) external onlyAdmin {
        require(account != address(0), "zero-account");
        if (!operators[account]) {
            operators[account] = true;
            operatorCount += 1;
            members.push(account);
        }
    }

    function grantAuditor(address account) external onlyAdmin {
        auditors[account] = true;
    }

    function revokeAll(address[] calldata accounts) external onlyAdmin {
        uint256 removed = 0;
        for (uint256 i = 0; i < accounts.length; i++) {
            if (operators[accounts[i]]) {
                operators[accounts[i]] = false;
                removed += 1;
            }
        }
        operatorCount -= removed;
        emit MembersPurged(removed);
    }

    function countOperators() external view onlyOperator returns (uint256 c) {
        for (uint256 i = 0; i < members.length; i++) {
            if (operators[members[i]]) {
                c += 1;
            }
        }
    }
}
