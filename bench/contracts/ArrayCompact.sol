// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ArrayCompact {
    uint256[] public items;

    function seed(uint256[] calldata xs) external {
        delete items;
        for (uint256 i = 0; i < xs.length; i++) {
            items.push(xs[i]);
        }
    }

    function removeZeros() external returns (uint256 removed) {
        uint256 write = 0;
        for (uint256 read = 0; read < items.length; read++) {
            if (items[read] != 0) {
                items[write] = items[read];
                write += 1;
            } else {
                removed += 1;
            }
        }
        while (items.length > write) {
            items.pop();
        }
    }

    function swapAndPop(uint256 target) external returns (uint256 removed) {
        uint256 i = 0;
        while (i < items.length) {
            if (items[i] == target) {
                items[i] = items[items.length - 1];
                items.pop();
                removed += 1;
            } else {
                i++;
            }
        }
    }

    function length() external view returns (uint256) {
        return items.length;
    }
}
