// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Escrow {
    address public arbiter;
    address[] public beneficiaries;
    mapping(address => uint256) public owed;
    uint256 public totalOwed;
    bool public released;

    event Released(uint256 paid, uint256 count);

    modifier onlyArbiter() {
        require(msg.sender == arbiter, "not-arbiter");
        _;
    }

    constructor() {
        arbiter = msg.sender;
    }

    function deposit(address beneficiary) external payable {
        require(beneficiary != address(0), "zero-beneficiary");
        if (owed[beneficiary] == 0) {
            beneficiaries.push(beneficiary);
        }
        owed[beneficiary] += msg.value;
        totalOwed += msg.value;
    }

    function releaseAll() external onlyArbiter {
        require(!released, "already-released");
        released = true;
        uint256 paid = 0;
        for (uint256 i = 0; i < beneficiaries.length; i++) {
            uint256 amount = owed[beneficiaries[i]];
            owed[beneficiaries[i]] = 0;
            paid += amount;
            payable(beneficiaries[i]).transfer(amount);
        }
        totalOwed -= paid;
        emit Released(paid, beneficiaries.length);
    }

    function releaseUnsafe() external onlyArbiter {
        for (uint256 i = 0; i < beneficiaries.length; i++) {
            uint256 amount = owed[beneficiaries[i]];
            (bool ok, ) = payable(beneficiaries[i]).call{value: amount}("");
            require(ok, "send-failed");
            owed[beneficiaries[i]] = 0;
        }
    }

    receive() external payable {}
}
