"""Compatibility entrypoint: one canonical current cart-plan generator."""
import runpy
from pathlib import Path
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('build_cart_plan.py')), run_name='__main__')
