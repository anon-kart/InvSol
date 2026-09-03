// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * LoopPlayground
 * - Has several functions with loops (for inference)
 * - Emits events aligned with your IR
 * - Uses _requireBound(n, maxN) in places per IR
 * - Public state to expose auto-getters (numbers, grid, deposits, depositorKeys)
 */
contract LoopPlayground {
    // -----------------------
    // State
    // -----------------------
    uint256[] public numbers;
    uint256[][] public grid;

    mapping(address => uint256) public deposits;
    address[] public depositorKeys;

    // -----------------------
    // Events (match IR names)
    // -----------------------
    event SumResult(uint256 total);
    event FoundAt(int256 index);
    event Sorted(uint256 n);
    event MatrixDot(uint256 r, uint256 c, uint256 val);
    event Filled(uint256 n);
    event UpdatedDeposit(address indexed who, uint256 newTotal);
    event Accumulated(uint256 total, uint256 counted);

    // -----------------------
    // Internal precondition helper
    // -----------------------

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: (n <= maxN)
    function _requireBound(uint256 n, uint256 maxN) internal pure {
        require(n <= maxN, "n > maxN");
    }

    // -----------------------
    // Constructor
    // - iterates over seed and seeds numbers/grid
    // -----------------------

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: HasExternalCalls()
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < seed.length
// POST_EXPR [loop#0]: HasExternalCallsInLoop()
// POST_EXPR [loop#0]: Guard((i < seed.length))
// POST_EXPR [loop#0]: Update((i++))
    constructor(uint256[] memory seed) {
        // Fill numbers with seed
        for (uint256 i = 0; i < seed.length; i++) {
            numbers.push(seed[i]); // dynamic array push (treated as external-ish call in many analyzers)
        }

        // Also seed grid with a single row equal to seed
        grid.push(seed);
    }

    // -----------------------
    // Simple queries
    // -----------------------

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
    function numbersLen() external view returns (uint256) {
        return numbers.length;
    }

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
    function gridDims() external view returns (uint256 rows, uint256 cols) {
        rows = grid.length;
        cols = (rows == 0) ? 0 : grid[0].length;
    }

    // -----------------------
    // Loops: scans & sums
    // -----------------------

    /// Sum the first `limit` numbers (bounded loop)

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(SumResult)
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < n
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Accumulator(sum:s)
// POST_EXPR [loop#0]: Guard((i < n))
// POST_EXPR [loop#0]: Update((i++))
    function sumNumbersBounded(uint256 limit) external returns (uint256) {
        uint256 n = (limit < numbers.length) ? limit : numbers.length;
        uint256 s = 0;
        for (uint256 i = 0; i < n; i++) {
            s += numbers[i];
        }
        emit SumResult(s);
        return s;
    }

    /// Same as above but leaves the loop update expression empty in source (to tick your IR boxes)

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(SumResult)
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < n
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Accumulator(sum:s)
// POST_EXPR [loop#0]: Guard((i < n))
    function sumUnchecked(uint256 limit) external returns (uint256) {
        uint256 n = (limit < numbers.length) ? limit : numbers.length;
        uint256 s = 0;
        for (uint256 i = 0; i < n;) {
            s += numbers[i];
            unchecked { ++i; } // manual update
        }
        emit SumResult(s);
        return s;
    }

    /// Find first index where numbers[i] > x, else -1

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(FoundAt)
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < numbers.length
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Guard((i < numbers.length))
// POST_EXPR [loop#0]: Update((i++))
    function firstGreaterThan(uint256 x) external returns (int256) {
        for (uint256 i = 0; i < numbers.length; i++) {
            if (numbers[i] > x) {
                emit FoundAt(int256(i));
                return int256(i);
            }
        }
        emit FoundAt(-1);
        return -1;
    }

    /// Sum all grid cells; emit per-cell (MatrixDot) and final total (SumResult)

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(MatrixDot)
// POST_EXPR: Emits(SumResult)
// POST_EXPR [loop#0]: 0 <= r
// POST_EXPR [loop#0]: r < grid.length
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Accumulator(sum:total)
// POST_EXPR [loop#0]: Guard((r < grid.length))
// POST_EXPR [loop#0]: Update((r++))
// POST_EXPR [loop#1]: 0 <= c
// POST_EXPR [loop#1]: c < row.length
// POST_EXPR [loop#1]: NoExternalCallsInLoop()
// POST_EXPR [loop#1]: Accumulator(sum:total)
// POST_EXPR [loop#1]: Guard((c < row.length))
// POST_EXPR [loop#1]: Update((c++))
    function sumGridDots() external returns (uint256) {
        uint256 total = 0;
        for (uint256 r = 0; r < grid.length; r++) {
            uint256[] storage row = grid[r];
            for (uint256 c = 0; c < row.length; c++) {
                uint256 v = row[c];
                total += v;
                emit MatrixDot(r, c, v);
            }
        }
        emit SumResult(total);
        return total;
    }

    // -----------------------
    // Writers with bounds
    // -----------------------

    /// Fill the first n entries of numbers with an arithmetic sequence

// --- Inferred Postconditions ---
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(Filled)
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < n
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Accumulator(cur:cur)
// POST_EXPR [loop#0]: UpdatesArray(numbers)
// POST_EXPR [loop#0]: Guard((i < n))
// POST_EXPR [loop#0]: Update((i++))
    function fillSequence(
        uint256 n,
        uint256 start,
        uint256 step,
        uint256 maxN
    ) external {
        _requireBound(n, maxN);

        // Ensure length >= n
        if (numbers.length < n) {
            uint256 toAdd = n - numbers.length;
            for (uint256 k = 0; k < toAdd;) {
                numbers.push(0);
                unchecked { ++k; }
            }
        }

        uint256 cur = start;
        for (uint256 i = 0; i < n; i++) {
            numbers[i] = cur;
            cur += step;
        }
        emit Filled(n);
    }

    /// Append n values numbers.push(base + i)

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: HasExternalCalls()
// POST_EXPR: Emits(Filled)
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < n
// POST_EXPR [loop#0]: HasExternalCallsInLoop()
// POST_EXPR [loop#0]: Guard((i < n))
    function appendMany(uint256 n, uint256 base, uint256 maxN) external {
        _requireBound(n, maxN);
        for (uint256 i = 0; i < n;) {
            numbers.push(base + i); // dynamic push (external call in IR sense)
            unchecked { ++i; }
        }
        emit Filled(n);
    }

    /// Bubble sort a local copy of numbers; return the sorted copy

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(Sorted)
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < n
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Guard((i < n))
// POST_EXPR [loop#0]: Update((i++))
// POST_EXPR [loop#1]: 0 <= i
// POST_EXPR [loop#1]: i < (n - 1)
// POST_EXPR [loop#1]: NoExternalCallsInLoop()
// POST_EXPR [loop#1]: Guard((i < (n - 1)))
// POST_EXPR [loop#1]: Update((i++))
// POST_EXPR [loop#2]: 0 <= j
// POST_EXPR [loop#2]: j < ((n - 1) - i)
// POST_EXPR [loop#2]: NoExternalCallsInLoop()
// POST_EXPR [loop#2]: Guard((j < ((n - 1) - i)))
// POST_EXPR [loop#2]: Update((j++))
    function bubbleSortLocal(uint256 maxN) external returns (uint256[] memory) {
        uint256 n = numbers.length;
        _requireBound(n, maxN);

        uint256[] memory arr = new uint256[](n);
        for (uint256 i = 0; i < n; i++) arr[i] = numbers[i];

        if (n > 1) {
            for (uint256 i = 0; i < n - 1; i++) {
                for (uint256 j = 0; j < (n - 1) - i; j++) {
                    if (arr[j] > arr[j + 1]) {
                        (arr[j], arr[j + 1]) = (arr[j + 1], arr[j]);
                    }
                }
            }
        }

        emit Sorted(n);
        return arr;
    }

    /// Triangular accumulation with nested loops; pure + bound precondition

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: (n <= maxN)
// POST_EXPR [loop#0]: 1 <= i
// POST_EXPR [loop#0]: i <= n
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Accumulator(sum:total)
// POST_EXPR [loop#0]: Guard((i <= n))
// POST_EXPR [loop#0]: Update((i++))
// POST_EXPR [loop#1]: 1 <= j
// POST_EXPR [loop#1]: j <= i
// POST_EXPR [loop#1]: NoExternalCallsInLoop()
// POST_EXPR [loop#1]: Accumulator(sum:total)
// POST_EXPR [loop#1]: Guard((j <= i))
// POST_EXPR [loop#1]: Update((j++))
    function triangularAccumulate(uint256 n, uint256 maxN) external pure returns (uint256) {
        require(n <= maxN, "n > maxN");
        uint256 total = 0;
        for (uint256 i = 1; i <= n; i++) {
            for (uint256 j = 1; j <= i; j++) {
                total += j;
            }
        }
        return total;
    }

    /// Scale-add constant to every cell in grid, return new total sum

// --- Inferred Postconditions ---
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(SumResult)
// POST_EXPR [loop#0]: 0 <= r
// POST_EXPR [loop#0]: r < grid.length
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: UpdatesArray(grid)
// POST_EXPR [loop#0]: Guard((r < grid.length))
// POST_EXPR [loop#0]: Update((r++))
// POST_EXPR [loop#1]: 0 <= c
// POST_EXPR [loop#1]: c < row.length
// POST_EXPR [loop#1]: NoExternalCallsInLoop()
// POST_EXPR [loop#1]: UpdatesArray(grid)
// POST_EXPR [loop#1]: Guard((c < row.length))
// POST_EXPR [loop#1]: Update((c++))
    function scaledAddToGrid(uint256 scale, uint256 /*maxCells*/) external returns (uint256) {
        uint256 total = 0;
        for (uint256 r = 0; r < grid.length; r++) {
            uint256[] storage row = grid[r];
            for (uint256 c = 0; c < row.length; c++) {
                row[c] += scale;
                total += row[c];
            }
        }
        emit SumResult(total);
        return total;
    }

    /// Push a new row into the grid (checks bound on columns)

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: HasExternalCalls()
    function pushRow(uint256[] memory row, uint256 maxCols) external {
        _requireBound(row.length, maxCols);
        grid.push(row); // dynamic push (external call in IR sense)
    }

    // -----------------------
    // Ether / accounting
    // -----------------------

// --- Inferred Postconditions ---
// POST_EXPR: HasExternalCalls()
// POST_EXPR: Emits(UpdatedDeposit)
    function deposit() external payable {
        bool first = (deposits[msg.sender] == 0 && msg.value > 0);
        deposits[msg.sender] += msg.value;
        if (first) {
            depositorKeys.push(msg.sender); // dynamic push (external call in IR sense)
        }
        emit UpdatedDeposit(msg.sender, deposits[msg.sender]);
    }

    /// Accumulate up to `limit` deposits by iterating depositorKeys

// --- Inferred Postconditions ---
// POST_EXPR: NoStateWrites()
// POST_EXPR: NoExternalCalls()
// POST_EXPR: Emits(Accumulated)
// POST_EXPR [loop#0]: 0 <= i
// POST_EXPR [loop#0]: i < n
// POST_EXPR [loop#0]: NoExternalCallsInLoop()
// POST_EXPR [loop#0]: Accumulator(sum:total)
// POST_EXPR [loop#0]: Guard((i < n))
// POST_EXPR [loop#0]: Update((i++))
    function accumulateDeposits(uint256 limit) external returns (uint256, uint256) {
        uint256 len = depositorKeys.length;
        uint256 n = (limit < len) ? limit : len;
        uint256 total = 0;
        for (uint256 i = 0; i < n; i++) {
            address acct = depositorKeys[i];
            total += deposits[acct];
        }
        emit Accumulated(total, n);
        return (total, n);
    }
}

