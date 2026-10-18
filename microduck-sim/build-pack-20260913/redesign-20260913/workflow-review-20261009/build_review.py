"""Current staged CAD review entry point."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/"roof-wiring-stage/build_review.py"),run_name="__main__")
