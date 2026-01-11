import sys
from pathlib import Path

# Ensure the pkg directory is on PYTHONPATH for imports
sys.path.insert(0, str(Path(__file__).parent / "pkg"))
