// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract BoundedQueue {
    uint256 public constant CAPACITY = 8;
    uint256[8] public slots;
    uint256 public head;
    uint256 public size;

    event Wrapped(uint256 head);

    function push(uint256 value) external {
        uint256 index = (head + size) % CAPACITY;
        slots[index] = value;
        if (size < CAPACITY) {
            size += 1;
        } else {
            head = (head + 1) % CAPACITY;
            emit Wrapped(head);
        }
    }

    function sum() external view returns (uint256 acc) {
        for (uint256 i = 0; i < size; i++) {
            acc += slots[(head + i) % CAPACITY];
        }
    }

    function fill(uint256[] calldata xs) external returns (uint256 written) {
        for (uint256 i = 0; i < xs.length && i < CAPACITY; i++) {
            slots[i] = xs[i];
            written += 1;
        }
        size = written;
        head = 0;
    }

    function drain() external returns (uint256 acc) {
        while (size > 0) {
            acc += slots[head];
            slots[head] = 0;
            head = (head + 1) % CAPACITY;
            size -= 1;
        }
    }
}
