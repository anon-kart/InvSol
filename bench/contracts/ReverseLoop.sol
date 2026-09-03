// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ReverseLoop {
    uint256[] public buffer;

    function seed(uint256[] calldata xs) external {
        delete buffer;
        for (uint256 i = 0; i < xs.length; i++) {
            buffer.push(xs[i]);
        }
    }

    function sumBackwards() external view returns (uint256 acc) {
        for (uint256 i = buffer.length; i > 0; i--) {
            acc += buffer[i - 1];
        }
    }

    function countdown(uint256 n) external pure returns (uint256 steps) {
        for (uint256 i = n; i > 0; i--) {
            steps += 1;
        }
    }

    function reversed() external view returns (uint256[] memory out) {
        uint256 n = buffer.length;
        out = new uint256[](n);
        for (uint256 i = 0; i < n; i++) {
            out[i] = buffer[n - 1 - i];
        }
    }

    function halve(uint256 start) external pure returns (uint256 iterations) {
        uint256 v = start;
        while (v > 1) {
            v = v / 2;
            iterations += 1;
        }
    }
}
