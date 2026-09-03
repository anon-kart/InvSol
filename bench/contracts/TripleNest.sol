// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract TripleNest {
    uint256 public checksum;

    function cube(uint256 a, uint256 b, uint256 c) external pure returns (uint256 total) {
        require(a <= 16 && b <= 16 && c <= 16, "bounds");
        for (uint256 i = 0; i < a; i++) {
            for (uint256 j = 0; j < b; j++) {
                for (uint256 k = 0; k < c; k++) {
                    total += i * j + k;
                }
            }
        }
    }

    function triangular(uint256 n, uint256 maxN) external pure returns (uint256 total) {
        require(n <= maxN, "too-big");
        for (uint256 i = 1; i <= n; i++) {
            for (uint256 j = 1; j <= i; j++) {
                total += j;
            }
        }
    }

    function record(uint256 a, uint256 b) external returns (uint256 total) {
        for (uint256 i = 0; i < a; i++) {
            for (uint256 j = 0; j < b; j++) {
                total += 1;
            }
        }
        checksum = total;
    }
}
