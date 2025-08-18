// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MyContract {
    uint public total;
    uint public threshold;

    constructor(uint _threshold) {
        total = 0;
        threshold = _threshold;
    }

    function updateTotal(uint x, uint y) public {
        require(x > 0 && y > 0 && x < 100, "Invalid input");

        for (uint i = 0; i < y; i++) {
            total += x;
        }

        assert(total >= x * y);
        assert(total >= threshold);
    }
}

