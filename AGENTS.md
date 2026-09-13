# Repository operating contract

Read `README.md`, `docs/THESIS.md`, `docs/PROBLEM_MAP.md`, `docs/ENTRY_STRATEGY.md`, and `DECISIONS.md` before changing direction.

- Work problem-first. Every substantial task must name the problem ID it advances and the evidence that would change the decision.
- Separate company claims, reproducible evidence, deployment evidence, and project inference. Record an official or primary source and verification date for non-obvious claims.
- A polished demo is not acceptance. Experiments need a baseline, perturbations, failure artifacts, and quantitative readback.
- Do not reduce the project to dashboards or integration glue. Infrastructure work is valuable only when it measurably improves the embodied learning loop.
- Keep course repositories independent. Never publish coursework or nested repository history through this root repository.
- On Shawn's machine, `~/code/memory` is the optional private source for personal facts and prior decisions. Search it only when relevant; never copy secrets or sensitive personal details into this public repository. Public project decisions belong in `DECISIONS.md`; private facts remain canonical in memory.
- Run `python3 scripts/validate_research.py` before committing research-map changes.
- Before MicroDuck procurement work or delegation, read `microduck-sim/build-pack-20260913/procurement/sourcing-policy.json` and its README. Preserve sourcing holds independently of engineering requirements; available stock and historical carts cannot release them. Regenerate the BOM/cart plan and run `test_sourcing.py` plus `verify_pack.py` in that directory before a purchasing handoff. Acceptance requires zero held items in purchase rows or mapped current carts; unmapped cart lines block handoff.
