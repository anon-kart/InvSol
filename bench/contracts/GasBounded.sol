// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract GasBounded {
    address[] public queue;
    mapping(address => uint256) public pending;
    uint256 public cursor;
    uint256 public batchSize;

    event BatchProcessed(uint256 from, uint256 to);

    constructor(uint256 batchSize_) {
        require(batchSize_ > 0, "zero-batch");
        batchSize = batchSize_;
    }

    function enqueue(address account, uint256 amount) external {
        if (pending[account] == 0) {
            queue.push(account);
        }
        pending[account] += amount;
    }

    function processBatch() external returns (uint256 processed) {
        uint256 end = cursor + batchSize;
        if (end > queue.length) {
            end = queue.length;
        }
        for (uint256 i = cursor; i < end; i++) {
            pending[queue[i]] = 0;
            processed += 1;
        }
        emit BatchProcessed(cursor, end);
        cursor = end;
    }

    function processAllUnbounded() external returns (uint256 processed) {
        for (uint256 i = 0; i < queue.length; i++) {
            pending[queue[i]] = 0;
            processed += 1;
        }
        cursor = queue.length;
    }

    function totalPending() external view returns (uint256 sum) {
        for (uint256 i = 0; i < queue.length; i++) {
            sum += pending[queue[i]];
        }
    }
}
