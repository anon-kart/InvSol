// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract TokenVesting {
    struct Schedule {
        uint256 start;
        uint256 interval;
        uint256 amountPerInterval;
        uint256 intervals;
        uint256 claimedIntervals;
    }

    address public owner;
    address[] public grantees;
    mapping(address => Schedule) public schedules;
    uint256 public totalVested;

    modifier onlyOwner() {
        require(msg.sender == owner, "not-owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function grant(
        address account,
        uint256 interval,
        uint256 amountPerInterval,
        uint256 intervals
    ) external onlyOwner {
        require(account != address(0), "zero-account");
        require(intervals <= 120, "too-many-intervals");
        grantees.push(account);
        schedules[account] = Schedule({
            start: block.timestamp,
            interval: interval,
            amountPerInterval: amountPerInterval,
            intervals: intervals,
            claimedIntervals: 0
        });
    }

    function vestedFor(address account) public view returns (uint256 vested) {
        Schedule storage s = schedules[account];
        for (uint256 i = 0; i < s.intervals; i++) {
            if (block.timestamp >= s.start + (i + 1) * s.interval) {
                vested += s.amountPerInterval;
            }
        }
    }

    function totalOutstanding() external view returns (uint256 sum) {
        for (uint256 i = 0; i < grantees.length; i++) {
            sum += vestedFor(grantees[i]);
        }
    }

    function claimElapsed() external returns (uint256 claimedNow) {
        Schedule storage s = schedules[msg.sender];
        uint256 i = s.claimedIntervals;
        while (i < s.intervals && block.timestamp >= s.start + (i + 1) * s.interval) {
            claimedNow += s.amountPerInterval;
            i++;
        }
        s.claimedIntervals = i;
        totalVested += claimedNow;
    }
}
