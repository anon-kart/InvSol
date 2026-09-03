// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract BatchTransfer {
    address public owner;
    uint256 public totalSupply;
    mapping(address => uint256) public balances;

    event BatchSent(uint256 recipients, uint256 moved);

    modifier onlyOwner() {
        require(msg.sender == owner, "not-owner");
        _;
    }

    constructor(uint256 supply) {
        owner = msg.sender;
        totalSupply = supply;
        balances[msg.sender] = supply;
    }

    function batchSend(address[] calldata to, uint256[] calldata amounts) external onlyOwner {
        require(to.length == amounts.length, "length-mismatch");
        uint256 moved = 0;
        for (uint256 i = 0; i < to.length; i++) {
            require(to[i] != address(0), "zero-recipient");
            balances[msg.sender] -= amounts[i];
            balances[to[i]] += amounts[i];
            moved += amounts[i];
        }
        emit BatchSent(to.length, moved);
    }

    function airdropEqual(address[] calldata to, uint256 amount) external onlyOwner {
        for (uint256 i = 0; i < to.length; i++) {
            balances[to[i]] += amount;
            totalSupply += amount;
        }
    }
}
