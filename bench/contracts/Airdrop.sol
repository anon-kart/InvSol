// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Airdrop {
    address public owner;
    uint256 public maxSupply;
    uint256 public minted;
    mapping(address => uint256) public claimed;
    mapping(uint256 => address) public ownerOf;

    event Minted(address to, uint256 tokenId);

    modifier onlyOwner() {
        require(msg.sender == owner, "not-owner");
        _;
    }

    constructor(uint256 cap) {
        owner = msg.sender;
        maxSupply = cap;
    }

    function batchMint(address[] calldata to) external onlyOwner {
        for (uint256 i = 0; i < to.length; i++) {
            require(minted < maxSupply, "cap-reached");
            ownerOf[minted] = to[i];
            claimed[to[i]] += 1;
            minted += 1;
            emit Minted(to[i], minted);
        }
    }

    function mintRun(address to, uint256 quantity) external onlyOwner {
        require(minted + quantity <= maxSupply, "would-exceed-cap");
        for (uint256 i = 0; i < quantity; i++) {
            ownerOf[minted + i] = to;
        }
        minted += quantity;
        claimed[to] += quantity;
    }

    function remaining() external view returns (uint256) {
        return maxSupply - minted;
    }
}
