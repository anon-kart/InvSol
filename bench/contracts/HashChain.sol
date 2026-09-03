// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract HashChain {
    bytes32 public root;
    uint256 public depth;

    function setRoot(bytes32 root_, uint256 depth_) external {
        require(depth_ <= 32, "depth-too-large");
        root = root_;
        depth = depth_;
    }

    function computeRoot(bytes32 leaf, bytes32[] calldata proof) external pure returns (bytes32 node) {
        node = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            if (node < proof[i]) {
                node = keccak256(abi.encodePacked(node, proof[i]));
            } else {
                node = keccak256(abi.encodePacked(proof[i], node));
            }
        }
    }

    function verify(bytes32 leaf, bytes32[] calldata proof) external view returns (bool) {
        bytes32 node = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            node = keccak256(abi.encodePacked(node, proof[i]));
        }
        return node == root;
    }

    function chain(bytes32 seed_, uint256 rounds) external pure returns (bytes32 node, uint256 steps) {
        require(rounds <= 64, "too-many-rounds");
        node = seed_;
        uint256 i = 0;
        while (i < rounds) {
            node = keccak256(abi.encodePacked(node));
            steps += 1;
            i++;
        }
    }
}
