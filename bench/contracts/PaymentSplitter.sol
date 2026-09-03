// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract PaymentSplitter {
    address public owner;
    address[] public payees;
    mapping(address => uint256) public shares;
    uint256 public totalShares;

    event Distributed(uint256 amount, uint256 payeeCount);

    modifier onlyOwner() {
        require(msg.sender == owner, "not-owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function addPayee(address account, uint256 share) external onlyOwner {
        require(account != address(0), "zero-payee");
        require(totalShares + share <= 100, "shares-exceed-100");
        payees.push(account);
        shares[account] = share;
        totalShares += share;
    }

    function distribute() external {
        uint256 initBal = address(this).balance;
        uint256 sumShares = 0;

        for (uint256 i = 0; i < payees.length; i++) {
            sumShares += shares[payees[i]];
            uint256 payment = (initBal * shares[payees[i]]) / 100;
            payable(payees[i]).transfer(payment);
        }

        emit Distributed(initBal, payees.length);
    }

    receive() external payable {}
}
