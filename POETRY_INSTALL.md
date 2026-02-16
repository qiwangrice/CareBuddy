# Install and setup (Poetry)

1. Install Poetry (recommended):

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Ensure Poetry is on your PATH (follow the installer output), then in the project root run:

```bash
poetry install
```

3. Optional: install `torch` separately because platform and CUDA/CPU options vary.

Example (CPU-only):

```bash
poetry add torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Or use the official selector at https://pytorch.org/get-started/locally/ to get the proper `poetry add` command for your system (CUDA, MPS, or CPU).

4. Run the script inside the Poetry environment:

```bash
poetry run python main.py
```
