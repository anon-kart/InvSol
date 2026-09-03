// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract VoteTally {
    struct Proposal {
        bytes32 name;
        uint256 voteCount;
    }

    Proposal[] public proposals;
    mapping(address => bool) public hasVoted;
    uint256 public totalVotes;
    uint256 public quorum;

    event Winner(uint256 index, uint256 votes);

    constructor(uint256 quorum_) {
        quorum = quorum_;
    }

    function addProposal(bytes32 name) external {
        proposals.push(Proposal({name: name, voteCount: 0}));
    }

    function vote(uint256 index) external {
        require(!hasVoted[msg.sender], "already-voted");
        require(index < proposals.length, "bad-index");
        hasVoted[msg.sender] = true;
        proposals[index].voteCount += 1;
        totalVotes += 1;
    }

    function tally() external view returns (uint256 sum) {
        for (uint256 i = 0; i < proposals.length; i++) {
            sum += proposals[i].voteCount;
        }
    }

    function winner() external returns (uint256 best) {
        uint256 highest = 0;
        for (uint256 i = 0; i < proposals.length; i++) {
            if (proposals[i].voteCount > highest) {
                highest = proposals[i].voteCount;
                best = i;
            }
        }
        emit Winner(best, highest);
    }

    function reachedQuorum() external view returns (bool) {
        uint256 counted = 0;
        for (uint256 i = 0; i < proposals.length; i++) {
            counted += proposals[i].voteCount;
            if (counted >= quorum) {
                return true;
            }
        }
        return false;
    }
}
