import sys
import os
from generator.main import process_contract

def main():
    if len(sys.argv) != 3:
        print("Usage: python run_generator.py <input.sol> <output.t.sol>")
        return

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' does not exist.")
        return

    try:
        process_contract(input_path, output_path)
        print(f"✅ Generated test file: {output_path}")
    except Exception as e:
        print(f"❌ Error during generation: {e}")

if __name__ == "__main__":
    main()
