import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "config.json"
OUTPUT_DIR = ROOT_DIR / "output"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_skill_module(script_path: str):
    full_path = ROOT_DIR / script_path
    spec = importlib.util.spec_from_file_location("skill_module", full_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="AI Integrator Lab orchestrator")
    parser.add_argument("company", help="Name of the target company")
    args = parser.parse_args()

    config = load_config()
    active_key = config["active_skill"]
    skill_config = config["skills"][active_key]

    module = load_skill_module(skill_config["script"])

    if not hasattr(module, "run"):
        print(f"Error: skill module '{skill_config['script']}' does not expose a run() function.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = module.run(args.company, OUTPUT_DIR)

    print(f"Skill '{skill_config['name']}' completed.")
    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
