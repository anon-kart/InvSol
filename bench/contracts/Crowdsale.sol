// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Crowdsale {
    address public owner;
    uint256 public cap;
    uint256 public raised;
    uint256 public deadline;
    address[] public contributors;
    mapping(address => uint256) public contributions;

    event Closed(uint256 raised, uint256 backers);

    modifier onlyOwner() {
        require(msg.sender == owner, "not-owner");
        _;
    }

    constructor(uint256 cap_, uint256 duration) {
        owner = msg.sender;
        cap = cap_;
        deadline = block.timestamp + duration;
    }

    function contribute() external payable {
        require(block.timestamp < deadline, "closed");
        require(raised + msg.value <= cap, "cap-exceeded");
        if (contributions[msg.sender] == 0) {
            contributors.push(msg.sender);
        }
        contributions[msg.sender] += msg.value;
        raised += msg.value;
    }

    function totalContributed() external view returns (uint256 sum) {
        for (uint256 i = 0; i < contributors.length; i++) {
            sum += contributions[contributors[i]];
        }
    }

    function backersAbove(uint256 minimum) external view returns (uint256 c) {
        for (uint256 i = 0; i < contributors.length; i++) {
            if (contributions[contributors[i]] >= minimum) {
                c += 1;
            }
        }
    }

    function extendWhileUnderCap(uint256 step) external onlyOwner returns (uint256 added) {
        while (raised + added + step <= cap) {
            added += step;
        }
    }
}
