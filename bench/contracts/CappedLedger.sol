// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// Every element written into a slot is clamped to a cap the contract stores,
/// so a claim over all elements is true without being implied by their type.
/// The corpus otherwise fills arrays straight from fuzzer input, where nothing
/// bounds the contents and no quantified property holds.
contract CappedLedger {
    uint256 public cap;
    uint256 public total;
    uint256[] public amounts;
    address[] public owners;

    constructor(uint256 cap_) {
        cap = cap_ == 0 ? 100 : cap_;
    }

    function record(uint256[] calldata values) external {
        for (uint256 i = 0; i < values.length && i < 32; i++) {
            uint256 clamped = values[i] % (cap + 1);
            amounts.push(clamped);
            total += clamped;
        }
    }

    function rescale(uint256 divisor) external {
        uint256 d = divisor == 0 ? 1 : divisor;
        for (uint256 i = 0; i < amounts.length; i++) {
            amounts[i] = amounts[i] / d;
        }
    }

    function trimTo(uint256 ceiling) external {
        uint256 c = ceiling > cap ? cap : ceiling;
        for (uint256 i = 0; i < amounts.length; i++) {
            if (amounts[i] > c) {
                amounts[i] = c;
            }
        }
    }

    function enrol(address who) external {
        owners.push(who);
    }

    function amountsLen() external view returns (uint256) {
        return amounts.length;
    }
}
