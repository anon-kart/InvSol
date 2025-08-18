# InvSol: Automated Invariant Generation & Verification for Solidity

---

## 🛠️ Prerequisites

Ensure the following utilities are installed:

- Python 3.10+
- Java 11+
- `solc` (Solidity compiler) → `sudo snap install solc`

- JDK tools (for JAR execution and class file handling)

Python packages:
```bash
pip install antlr4-python3-runtime
```
InvSol/
└── src/
    ├── ast_tsol_generator/     
    ├── LoopSynth/              
    ├── foundry2daikon/         
    ├── dynamic_inv_gen/        
    └── static_code_auditor/    

# Step 1: Go to project root
cd InvSol/

# Step 2: Run invariant inference via fat.py
python3 src/LoopSynth/dynamate-sol/ginpink-sol/fat.py \
  -P 4 \
  -T path/to/theory_dir/ \
  path/to/contract.sol
