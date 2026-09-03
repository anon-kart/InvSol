// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract DoWhileAccumulate {
    uint256 public lastResult;

    function sumTo(uint256 n, uint256 maxN) external pure returns (uint256 acc) {
        require(n <= maxN, "n-too-large");
        uint256 i = 0;
        do {
            acc += i;
            i++;
        } while (i <= n);
    }

    function digits(uint256 value) external pure returns (uint256 count) {
        uint256 v = value;
        do {
            count += 1;
            v = v / 10;
        } while (v > 0);
    }

    function accumulate(uint256 n) external returns (uint256 acc) {
        uint256 i = 0;
        do {
            acc += i * 2;
            i++;
        } while (i < n);
        lastResult = acc;
    }
}
