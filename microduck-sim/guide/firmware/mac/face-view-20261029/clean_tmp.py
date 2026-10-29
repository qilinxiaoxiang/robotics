"""Delete the temporary head-command files sim_batch.dance_file left in results/ (explicit paths, pathlib)."""
import pathlib

RES = pathlib.Path(__file__).resolve().parent / "results"
for p in sorted(RES.glob("tmp*.json")):
    p.unlink()
    print("removed", p.name)
