# Research method: evidence before excitement

## Evidence ladder

| Level | Meaning | Allowed wording |
|---|---|---|
| E0 | Thesis or project inference | “We believe” / “our hypothesis” |
| E1 | Company plan or announcement | “announced,” never “achieved” |
| E2 | First-party demonstration | “demonstrated under published conditions” |
| E3 | Open artifact or reproducible benchmark | “reproducible from released code/data,” with limitations |
| E4 | Named customer pilot or repeated field use | “piloted/deployed at X,” with scope and duration |
| E5 | Independent, repeated validation | “independently validated,” with direct evidence |

Funding, valuation, video popularity, and founder reputation do not raise an evidence level.

## Required fields for a company update

- claim and exact date;
- official or primary source URL;
- evidence level;
- relevant problem IDs from `P0`–`P7`;
- what changed in our judgment;
- what evidence would reverse that judgment.

## Required fields for an experiment

- problem ID and hypothesis;
- baseline and competing explanation;
- train/validation/test separation;
- robot, simulator, task, controller, and data provenance;
- seeds and perturbations;
- success, failure, recovery, human burden, and system metrics;
- raw artifacts and exact reproduction command;
- decision: continue, change route, or stop.

## Freshness rule

The company landscape is time-sensitive. Active-company claims older than 90 days are stale until their official source is re-read. Papers and stable technical definitions can use longer review intervals, but versioned tools and model availability must be verified live before execution.

## Source discipline

1. Papers, released repositories, official technical documentation, and named deployment evidence come first.
2. Company posts are valid for what the company claims, not for independent proof.
3. Secondary reporting is used for context or contradiction, never to replace an available primary source.
4. Every synthesis that goes beyond a source is labeled as project judgment or inference.
5. Impressive demonstrations are deliberately stress-tested for resets, teleoperation, cherry-picking, hidden fixtures, and missing denominators.

## Public/private boundary

The public repository stores research judgments and reproducible project evidence. Personal facts, credentials, private conversations, and unrelated career or financial context remain outside this repository. Local agents may consult the private memory source when a decision genuinely depends on it, but only the resulting non-sensitive project decision is written here.
