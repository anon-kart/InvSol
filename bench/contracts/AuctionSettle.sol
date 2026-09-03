// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract AuctionSettle {
    address public seller;
    address[] public bidders;
    mapping(address => uint256) public bids;
    address public highestBidder;
    uint256 public highestBid;
    bool public settled;

    event Settled(address winner, uint256 amount, uint256 refunds);

    modifier onlySeller() {
        require(msg.sender == seller, "not-seller");
        _;
    }

    constructor() {
        seller = msg.sender;
    }

    function bid() external payable {
        require(!settled, "auction-over");
        require(msg.value > 0, "zero-bid");
        if (bids[msg.sender] == 0) {
            bidders.push(msg.sender);
        }
        bids[msg.sender] += msg.value;
        if (bids[msg.sender] > highestBid) {
            highestBid = bids[msg.sender];
            highestBidder = msg.sender;
        }
    }

    function settle() external onlySeller {
        require(!settled, "already-settled");
        settled = true;
        uint256 refunds = 0;
        for (uint256 i = 0; i < bidders.length; i++) {
            if (bidders[i] != highestBidder) {
                uint256 amount = bids[bidders[i]];
                bids[bidders[i]] = 0;
                refunds += amount;
                payable(bidders[i]).transfer(amount);
            }
        }
        emit Settled(highestBidder, highestBid, refunds);
    }

    function totalBids() external view returns (uint256 sum) {
        for (uint256 i = 0; i < bidders.length; i++) {
            sum += bids[bidders[i]];
        }
    }

    receive() external payable {}
}
