// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract SumArray {
    uint256[] public values;
    uint256 public lastTotal;

    event Summed(uint256 total, uint256 count);

    function seed(uint256[] calldata xs) external {
        delete values;
        for (uint256 i = 0; i < xs.length; i++) {
            values.push(xs[i]);
        }
    }

    function total() external returns (uint256 acc) {
        for (uint256 i = 0; i < values.length; i++) {
            acc += values[i];
        }
        lastTotal = acc;
        emit Summed(acc, values.length);
    }

    function totalBounded(uint256 n, uint256 maxN) external view returns (uint256 acc) {
        require(n <= maxN, "n-too-large");
        require(n <= values.length, "n-out-of-range");
        for (uint256 i = 0; i < n; i++) {
            acc += values[i];
        }
    }

    function count() external view returns (uint256 c) {
        for (uint256 i = 0; i < values.length; i++) {
            c += 1;
        }
    }
}
