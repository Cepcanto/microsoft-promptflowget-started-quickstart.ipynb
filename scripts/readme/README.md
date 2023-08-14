# Default Usage

These tools is used to generate workflows from README.md and python notebook files in the [examples](../../examples/) folder.

## 1. Install dependencies

```bash
pip install -r ../../examples/requirements.txt
pip install -r ../../examples/dev_requirements.txt
```

## 2. Generate workflows

### (Option 1) One Step Generation

At the **root** of the repository, run the following command:

```bash
python scripts/readme/readme.py
```

### (Option 2) Step by Step Generation

At the **root** of the repository, run the following command:

```bash
# Generate workflow from README.md inside examples folder
python scripts/readme/readme_generator.py -g "examples/**/*.ipynb"

# Generate workflow from python notebook inside examples folder
python scripts/readme/workflow_generator.py -g "examples/flows/**/README.md"
```