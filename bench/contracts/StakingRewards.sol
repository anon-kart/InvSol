// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract StakingRewards {
    address public owner;
    address[] public stakers;
    mapping(address => uint256) public stakeOf;
    mapping(address => uint256) public rewardOf;
    uint256 public totalStaked;
    uint256 public rewardRate;

    modifier onlyOwner() {
        require(msg.sender == owner, "not-owner");
        _;
    }

    constructor(uint256 rate) {
        owner = msg.sender;
        rewardRate = rate;
    }

    function stake(uint256 amount) external {
        require(amount > 0, "zero-stake");
        if (stakeOf[msg.sender] == 0) {
            stakers.push(msg.sender);
        }
        stakeOf[msg.sender] += amount;
        totalStaked += amount;
    }

    function accrueAll() external onlyOwner returns (uint256 issued) {
        for (uint256 i = 0; i < stakers.length; i++) {
            uint256 reward = (stakeOf[stakers[i]] * rewardRate) / 100;
            rewardOf[stakers[i]] += reward;
            issued += reward;
        }
    }

    function totalStakedComputed() external view returns (uint256 sum) {
        for (uint256 i = 0; i < stakers.length; i++) {
            sum += stakeOf[stakers[i]];
        }
    }

    function topStaker() external view returns (address best) {
        uint256 highest = 0;
        for (uint256 i = 0; i < stakers.length; i++) {
            if (stakeOf[stakers[i]] > highest) {
                highest = stakeOf[stakers[i]];
                best = stakers[i];
            }
        }
    }
}
