// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0 <0.9.0;

contract DynamicSearch {
    uint256[] public data;
    uint256 public threshold;

    function seed(uint256[] calldata xs, uint256 t) external {
        delete data;
        for (uint256 i = 0; i < xs.length; i++) {
            data.push(xs[i]);
        }
        threshold = t;
    }

    function firstAbove() external view returns (uint256 index, bool found) {
        for (uint256 i = 0; i < data.length; i++) {
            if (data[i] > threshold) {
                return (i, true);
            }
        }
        return (0, false);
    }

    function drainWhile() external view returns (uint256 consumed) {
        uint256 i = 0;
        while (i < data.length && data[i] < threshold) {
            consumed += data[i];
            i++;
        }
    }

    function collectUntilBudget(uint256 budget) external view returns (uint256 taken) {
        uint256 i = 0;
        uint256 spent = 0;
        while (i < data.length) {
            if (spent + data[i] > budget) {
                break;
            }
            spent += data[i];
            taken += 1;
            i++;
        }
    }
}
