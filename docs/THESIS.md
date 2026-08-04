# Thesis: AI needs an experimental interface to reality

## The commitment

The project starts from this commitment:

> AI has become powerful in the digital world. Robots are the medium through which it can perceive, intervene in, and learn from the physical world. Once that feedback loop compounds, it can attack production, material, and scientific problems at a fundamentally different speed.

This is the project's north star, not a proposition that every experiment must re-prove.

## Five corrections that make the thesis operational

1. **Robot does not mean humanoid.** A humanoid is one bet on reusing human environments and demonstrations. Arms, mobile robots, autonomous vehicles, and laboratory workcells may close valuable loops sooner.
2. **A body is necessary but insufficient.** Intelligence needs a task, observations, an action-conditioned model, a policy, a verifier, memory, learning, and safe redeployment.
3. **World models must be judged by decisions, not visual fidelity.** A beautiful predicted video is useful only if it helps choose safer or more effective actions and stays calibrated under distribution shift.
4. **Self-improvement can self-corrupt.** A wrong reward, success detector, or data filter can amplify failure. Verification and regression gates are part of intelligence, not administrative overhead.
5. **Goal selection remains upstream.** Faster execution does not decide which scientific or material problem deserves pursuit. The project must preserve human control over objectives while progressively automating experiment design and execution.

## The causal chain

The end state is not “a smart robot.” It is a system that can repeatedly:

1. translate a meaningful goal into a testable physical task;
2. predict relevant consequences of candidate actions;
3. act safely and collect complete traces;
4. detect progress, success, failure, and uncertainty;
5. turn the most informative failures into new training data;
6. improve without regressing elsewhere;
7. redeploy and repeat at greater scale.

Every project in this repository must identify which link it strengthens and how that improvement will be observed.

## What is fixed and what remains falsifiable

**Fixed north star:** AI should gain a compounding interface to the physical world.

**Falsifiable implementation bets:**

- whether learned world models improve action choice better than simpler state estimators;
- whether humanoids are the dominant general-purpose body;
- whether simulation data transfers economically to real systems;
- whether generalist policies outperform task-specialized systems at useful reliability;
- whether the selected failure-to-data loop improves learning efficiency.

Keeping these layers separate lets conviction supply persistence without turning a technical preference into dogma.
