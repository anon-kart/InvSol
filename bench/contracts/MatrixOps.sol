// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract MatrixOps {
    uint256[][] public grid;
    uint256 public rows;
    uint256 public cols;

    function init(uint256 r, uint256 c) external {
        require(r <= 32 && c <= 32, "too-large");
        delete grid;
        rows = r;
        cols = c;
        for (uint256 i = 0; i < r; i++) {
            grid.push();
            for (uint256 j = 0; j < c; j++) {
                grid[i].push(i * c + j);
            }
        }
    }

    function sumAll() external view returns (uint256 total) {
        for (uint256 i = 0; i < grid.length; i++) {
            for (uint256 j = 0; j < grid[i].length; j++) {
                total += grid[i][j];
            }
        }
    }

    function scaleRegion(uint256 r, uint256 c, uint256 factor) external returns (uint256 touched) {
        require(r <= grid.length, "row-out-of-range");
        for (uint256 i = 0; i < r; i++) {
            for (uint256 j = 0; j < c && j < grid[i].length; j++) {
                grid[i][j] = grid[i][j] * factor;
                touched += 1;
            }
        }
    }

    function rowMax(uint256 r) external view returns (uint256 best) {
        require(r < grid.length, "row-out-of-range");
        for (uint256 j = 0; j < grid[r].length; j++) {
            if (grid[r][j] > best) {
                best = grid[r][j];
            }
        }
    }
}
