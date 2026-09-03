// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract OffByOne {
    uint256[] public items;

    function seed(uint256[] calldata xs) external {
        delete items;
        for (uint256 i = 0; i < xs.length; i++) {
            items.push(xs[i]);
        }
    }

    function sumCorrect() external view returns (uint256 acc) {
        for (uint256 i = 0; i < items.length; i++) {
            acc += items[i];
        }
    }

    function sumInclusiveBug() external view returns (uint256 acc) {
        for (uint256 i = 0; i <= items.length; i++) {
            acc += items[i];
        }
    }

    function copyShiftedBug(uint256 n) external view returns (uint256[] memory out) {
        require(n <= items.length, "n-out-of-range");
        out = new uint256[](n);
        for (uint256 i = 0; i <= n; i++) {
            out[i] = items[i];
        }
    }

    function lastWindow(uint256 k) external view returns (uint256 acc) {
        require(k <= items.length, "k-out-of-range");
        for (uint256 i = items.length - k; i < items.length; i++) {
            acc += items[i];
        }
    }
}
