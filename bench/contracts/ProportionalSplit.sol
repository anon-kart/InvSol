// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ProportionalSplit {
    address public owner;
    address[] public holders;
    mapping(address => uint256) public weight;
    uint256 public totalWeight;
    uint256 public constant SCALE = 100;

    modifier onlyOwner() {
        require(msg.sender == owner, "not-owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setWeight(address account, uint256 w) external onlyOwner {
        require(account != address(0), "zero-account");
        if (weight[account] == 0) {
            holders.push(account);
        }
        totalWeight = totalWeight - weight[account] + w;
        require(totalWeight <= SCALE, "weight-over-scale");
        weight[account] = w;
    }

    function allocate(uint256 pool) external view returns (uint256[] memory shares) {
        shares = new uint256[](holders.length);
        uint256 assigned = 0;
        for (uint256 i = 0; i < holders.length; i++) {
            uint256 share = (pool * weight[holders[i]]) / SCALE;
            shares[i] = share;
            assigned += share;
        }
    }

    function weightSum() external view returns (uint256 sum) {
        for (uint256 i = 0; i < holders.length; i++) {
            sum += weight[holders[i]];
        }
    }

    function normalise() external onlyOwner returns (uint256 leftover) {
        uint256 running = 0;
        for (uint256 i = 0; i < holders.length; i++) {
            running += weight[holders[i]];
            if (running > SCALE) {
                weight[holders[i]] = 0;
            }
        }
        leftover = SCALE - (running > SCALE ? SCALE : running);
        totalWeight = running > SCALE ? SCALE : running;
    }
}
