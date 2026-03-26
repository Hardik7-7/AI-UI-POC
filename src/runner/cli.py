import argparse
import sys
import os
import json
import subprocess
from dotenv import load_dotenv

# Add project root to python path so it can find src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.generator.test_generator import TestGenerator
from src.generator.code_generator import CodeGenerator
from src.models.schemas import TestSuite, TestScenario

SCENARIOS_DIR = "output/scenarios"
TESTS_DIR = "output/generated_tests"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_api_key():
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)


def _save_scenarios(suite: TestSuite, scenarios_path: str):
    """Serialize a TestSuite to a human-readable JSON scenarios file."""
    os.makedirs(os.path.dirname(scenarios_path), exist_ok=True)
    data = [sc.model_dump(by_alias=True) for sc in suite.scenarios]
    with open(scenarios_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_scenarios(scenarios_path: str) -> TestSuite:
    """Load a scenarios JSON file back into a TestSuite."""
    with open(scenarios_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return TestSuite(scenarios=[TestScenario(**sc) for sc in raw])


def _extract_and_save(workflow_path: str, generator: TestGenerator) -> str:
    """Run Phase 1 for a single workflow file. Returns the saved scenarios path."""
    print(f"\n  Processing: {workflow_path}")
    suite = generator.generate_scenarios_from_file(workflow_path)
    print(f"  -> {len(suite.scenarios)} scenario(s) extracted")
    for sc in suite.scenarios:
        print(f"     [{sc.scenario_name}]  {sc.description}")

    out_name = os.path.splitext(os.path.basename(workflow_path))[0] + "_scenarios.json"
    scenarios_path = os.path.join(SCENARIOS_DIR, out_name)
    _save_scenarios(suite, scenarios_path)
    print(f"  -> Saved: {scenarios_path}")
    return scenarios_path


# ---------------------------------------------------------------------------
# Subcommand: generate-scenarios
# ---------------------------------------------------------------------------

def cmd_generate_scenarios(args):
    """Phase 1: Extract scenarios from one or more workflow files."""
    _require_api_key()
    generator = TestGenerator()
    saved = []

    # Collect all workflow files to process
    workflow_files = []
    if hasattr(args, "input") and args.input:
        workflow_files.append(args.input)
    if hasattr(args, "input_dir") and args.input_dir:
        for fname in sorted(os.listdir(args.input_dir)):
            if fname.endswith(".txt") or fname.endswith(".md"):
                workflow_files.append(os.path.join(args.input_dir, fname))

    if not workflow_files:
        print("ERROR: Provide --input <file> or --input-dir <folder>")
        sys.exit(1)

    print(f"[Phase 1] Extracting scenarios from {len(workflow_files)} workflow file(s)...")
    for wf in workflow_files:
        try:
            path = _extract_and_save(wf, generator)
            saved.append(path)
        except Exception as e:
            print(f"  ERROR processing {wf}: {e}")

    print(f"\n[Done] {len(saved)}/{len(workflow_files)} workflow(s) processed.")
    print("\nNext: review the JSON files, then run:")
    print(f"  python src/runner/cli.py generate-code --scenarios-dir {SCENARIOS_DIR} --output-dir {TESTS_DIR}")


# ---------------------------------------------------------------------------
# Subcommand: generate-code
# ---------------------------------------------------------------------------

def cmd_generate_code(args):
    """Phase 2: Generate pytest files from one or more scenario JSON files."""
    coder = CodeGenerator()
    generated = []

    scenario_files = []
    if hasattr(args, "from_scenarios") and args.from_scenarios:
        scenario_files.append(args.from_scenarios)
    if hasattr(args, "scenarios_dir") and args.scenarios_dir:
        for fname in sorted(os.listdir(args.scenarios_dir)):
            if fname.endswith("_scenarios.json"):
                scenario_files.append(os.path.join(args.scenarios_dir, fname))

    if not scenario_files:
        print("ERROR: Provide --from-scenarios <file> or --scenarios-dir <folder>")
        sys.exit(1)

    print(f"[Phase 2] Generating test code from {len(scenario_files)} scenarios file(s)...")

    for sc_path in scenario_files:
        print(f"\n  Processing: {sc_path}")
        try:
            suite = _load_scenarios(sc_path)
            # Output filename: strip _scenarios.json → test_<name>.py
            base = os.path.splitext(os.path.basename(sc_path))[0]  # e.g. workflow_scenarios
            base = base.replace("_scenarios", "")                    # → workflow
            out_filename = getattr(args, "output", None) or f"test_{base}.py"

            # If processing multiple files, always derive the filename from the source
            if len(scenario_files) > 1 or getattr(args, "scenarios_dir", None):
                out_filename = f"test_{base}.py"

            filepath = coder.generate_pytest_file(suite, filename=out_filename)
            print(f"  -> Generated: {filepath}")
            generated.append(filepath)
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n[Done] {len(generated)} test file(s) generated.")
    print("\nTo run all tests at once:")
    print(f"  python src/runner/cli.py run-all")


# ---------------------------------------------------------------------------
# Subcommand: run-all
# ---------------------------------------------------------------------------

def cmd_run_all(args):
    """Run all generated test files sequentially."""
    test_dir = getattr(args, "test_dir", None) or TESTS_DIR

    test_files = sorted([
        os.path.join(test_dir, f)
        for f in os.listdir(test_dir)
        if f.startswith("test_") and f.endswith(".py")
    ])

    if not test_files:
        print(f"No test files found in {test_dir}")
        sys.exit(1)

    print(f"[run-all] Found {len(test_files)} test file(s) to run:\n")
    for t in test_files:
        print(f"  {t}")

    results = {}
    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"Running: {test_file}")
        print('='*60)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "-s"],
            cwd=os.getcwd()
        )
        results[test_file] = "PASSED" if result.returncode == 0 else "FAILED"

    # Summary
    print(f"\n{'='*60}")
    print("BATCH RUN SUMMARY")
    print('='*60)
    for path, status in results.items():
        icon = "✅" if status == "PASSED" else "❌"
        print(f"  {icon} {os.path.basename(path)}: {status}")

    failed = [k for k, v in results.items() if v == "FAILED"]
    if failed:
        sys.exit(1)


def cmd_self_heal(args):
    """Run deterministic tests and fallback to AI test for self-healing if they fail."""
    det_dir = os.path.join("output", "deterministic")
    ai_dir = os.path.join("output", "generated_tests")
    
    if not os.path.exists(det_dir):
        print(f"Directory {det_dir} not found. Run generate-code and run-all first.")
        sys.exit(1)

    det_files = sorted([f for f in os.listdir(det_dir) if f.startswith("test_") and f.endswith("_det.py")])
    if not det_files:
        print(f"No deterministic tests found in {det_dir}")
        sys.exit(1)

    print(f"\n[self-heal] Starting fast regression pass on {len(det_files)} deterministic tests...")
    
    failed_tests = []
    for test_file in det_files:
        path = os.path.join(det_dir, test_file)
        print(f"\n--- Running fast target: {test_file} ---")
        result = subprocess.run([sys.executable, "-m", "pytest", path, "-q"], cwd=os.getcwd())
        
        if result.returncode != 0:
            print(f"❌ Deterministic test failed: {test_file}")
            failed_tests.append(test_file)
        else:
            print(f"✅ Deterministic test passed (No AI needed): {test_file}")

    if not failed_tests:
        print("\n🎉 All deterministic tests passed! The UI is stable.")
        return

    print(f"\n⚠️ {len(failed_tests)} deterministic tests failed. Initiating AI Self-Healing...")

    # For each failure, map to the AI test and run it again to heal the script
    for failed_file in failed_tests:
        # e.g., 'test_verify_login_0_det.py' -> 'test_verify_login_0'
        func_name = failed_file.replace("_det.py", "")
        
        # Search for which AI test file contains this function
        ai_target_file = None
        for ai_file in os.listdir(ai_dir):
            if ai_file.startswith("test_") and ai_file.endswith(".py"):
                with open(os.path.join(ai_dir, ai_file), 'r', encoding='utf-8') as f:
                    if f"def {func_name}(" in f.read():
                        ai_target_file = ai_file
                        break
        
        if not ai_target_file:
            print(f"Could not find source AI test for {func_name} to heal it.")
            continue

        ai_target_path = os.path.join(ai_dir, ai_target_file)
        print(f"\n🔄 Self-Healing triggered for {func_name} (via {ai_target_file})")
        print("Launching CustomAgent with dom.js to find the new UI elements...")
        
        heal_result = subprocess.run(
            [sys.executable, "-m", "pytest", f"{ai_target_path}::{func_name}", "-v", "-s"],
            cwd=os.getcwd()
        )
        
        if heal_result.returncode == 0:
            print(f"✅ Successfully healed {failed_file}! New deterministic script saved.")
        else:
            print(f"❌ AI was unable to complete the workflow for {failed_file}. The UI might be broken.")


def cmd_publish_tests(args):
    """Consolidated pipeline: Generate Code -> Run AI Tests -> Self-Heal Deterministic"""
    print("\n" + "*"*70)
    print("🚀 STARTING E2E AUTOMATION PUBLISH PIPELINE")
    print("*"*70)
    
    print("\n[Stage 1/3] Generating AI test wrappers from approved JSON scenarios...")
    cmd_generate_code(args)
    
    print("\n[Stage 2/3] Executing AI tests to generate deterministic Playwright scripts...")
    cmd_run_all(args)
    
    print("\n[Stage 3/3] Running fast regression on deterministic scripts (with self-healing framework)...")
    cmd_self_heal(args)
    
    print("\n✅ PIPELINE COMPLETE! Deterministic tests are ready for CI/CD or Git Push.")


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="AI UI Test Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  generate-scenarios  Phase 1: Extract test scenarios from workflow(s) using AI
  generate-code       Phase 2: Generate pytest files from scenario JSON(s)  [no AI]
  run-all             Phase 3: Run all AI tests sequentially
  self-heal           Phase 4: Run deterministic tests; fallback to AI test if broken
  publish-tests       Master Command: Runs Phase 2, Phase 3, and Phase 4 sequentially

Examples:
  # Self-healing pipeline
  python src/runner/cli.py self-heal
  # The fully consolidated pipeline
  python src/runner/cli.py publish-tests --scenarios-dir output/scenarios/
"""
    )
    subparsers = parser.add_subparsers(dest="command")

    # generate-scenarios
    p1 = subparsers.add_parser("generate-scenarios", help="Phase 1: Extract scenarios from workflow(s) [uses AI]")
    p1_input = p1.add_mutually_exclusive_group(required=True)
    p1_input.add_argument("--input", help="Single workflow .txt file")
    p1_input.add_argument("--input-dir", help="Directory of workflow .txt/.md files (batch mode)")

    # generate-code
    p2 = subparsers.add_parser("generate-code", help="Phase 2: Generate pytest files from scenarios JSON(s) [no AI]")
    p2_input = p2.add_mutually_exclusive_group(required=True)
    p2_input.add_argument("--from-scenarios", help="Single scenarios .json file")
    p2_input.add_argument("--scenarios-dir", help="Directory of *_scenarios.json files (batch mode)")
    p2.add_argument("--output", default=None, help="Output filename (single file mode only)")

    # run-all
    p3 = subparsers.add_parser("run-all", help="Phase 3: Run all AI tests sequentially")
    p3.add_argument("--test-dir", default=TESTS_DIR, help=f"Directory with test files (default: {TESTS_DIR})")

    # self-heal
    p4 = subparsers.add_parser("self-heal", help="Run deterministic tests, heal automatically via AI if broken")

    # publish-tests
    p5 = subparsers.add_parser("publish-tests", help="Run Phase 2, 3, and 4 in a single pipeline")
    p5_input = p5.add_mutually_exclusive_group(required=True)
    p5_input.add_argument("--from-scenarios", help="Single scenarios .json file")
    p5_input.add_argument("--scenarios-dir", help="Directory of *_scenarios.json files (batch mode)")

    args = parser.parse_args()

    # Re-map arguments for subcommands when using publish-tests
    if args.command == "publish-tests":
        args.test_dir = TESTS_DIR  # Required for run-all
        
    if args.command == "generate-scenarios":
        cmd_generate_scenarios(args)
    elif args.command == "generate-code":
        cmd_generate_code(args)
    elif args.command == "run-all":
        cmd_run_all(args)
    elif args.command == "self-heal":
        cmd_self_heal(args)
    elif args.command == "publish-tests":
        cmd_publish_tests(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
