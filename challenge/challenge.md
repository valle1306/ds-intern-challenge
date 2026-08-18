# DS Intern Build Challenge

Target time: 90 minutes. Please stop at 2 hours.

Your goal is to build the smallest useful thing you can from a messy or underdefined problem. We care much more about judgment, clarity, and shipping than completeness.

AI tools are allowed. In fact, assume we expect you to use whatever tools help you move faster. What matters is whether you can guide those tools, verify important outputs, and make decisions they cannot make for you.

## The Prompt

Build **one** small artifact that helps a teammate understand, explore, predict, evaluate, or use something.

You choose the track, define the useful scope, and decide what is worth ignoring.

## Choose One Track

### Track A: Fictional Domain Packet

Read the domain packet:

- [domain-packet.md](domain-packet.md)

Then use the dataset:

- [sample-data/product_usage_events.csv](../sample-data/product_usage_events.csv)

A teammate on a fictional product team asks:

> We launched a few AI-assisted workflows for internal teams. Can you help us understand what is working, what looks suspicious, and what we should look at next?

This track is best if you want to show how you digest unfamiliar domain context, handle messy data, and turn a vague ask into something useful.

### Track B: Bring Your Own Domain

Pick a domain you understand, are curious about, or think you have good taste in.

Use a small public or synthetic dataset. Build something useful for a real imagined teammate, user, or decision-maker.

Examples of domains could include music, sports, public markets, student life, open-source projects, creator tools, games, local services, education, health/wellness with synthetic data, or anything else you can frame clearly.

This track is best if you want to show curiosity, taste, and domain framing.

### Track C: Tiny Model / Eval

Use a small model, prompt, heuristic, or evaluation workflow to answer a practical question in a domain you choose.

This could be a tiny classifier, a prediction heuristic, a prompt comparison, a model behavior check, an LLM eval, or a workflow that uses an existing model in a useful way.

We do **not** care about state-of-the-art performance. We care about the question you choose, the data you use, the assumptions you make, and how you decide whether the output is trustworthy.

Cloud GPUs or paid tools are not required and will not be scored higher. If you use one, keep it tiny and explain why.

## Acceptable Artifacts

Choose one:

- a short notebook;
- a small Streamlit app;
- a simple script with clear output;
- a lightweight web page;
- a tiny internal-tool style interface.

Please keep the scope tight. A polished small solution is better than a broad unfinished one.

## Deliverables

Please submit:

1. **Your artifact**
   - one working artifact;
   - focus on one core use case, not multiple features.

2. **A short `README.md`**
   - keep it under 300 words;
   - include your chosen track, what you built, who it is for, what data/source you used, assumptions, issues noticed, and what you would do next with more time.

3. **A short `AI_NOTE.md`**
   - whether you used AI;
   - how you used it;
   - one prompt, workflow, or moment where it helped;
   - one thing you verified or decided yourself instead of trusting AI blindly.

You may start from the templates in [templates/](templates/), or write your own.

## Constraints

- Do not build more than one main feature.
- Do not write a long report or slide deck.
- Do not use private, confidential, client, employer, or personal data.
- If you bring your own data, include the data, a small sample, or clear reproduction instructions.
- Do not scrape websites in ways that violate their terms.
- It is completely fine to make reasonable assumptions and move forward.
- You may use any tools you normally use, including AI tools.

## Guidance

A strong submission is:

- small;
- usable;
- clear;
- thoughtfully scoped;
- honest about assumptions and limitations;
- opinionated about what mattered and what did not.

A weaker submission is:

- overly broad;
- half-finished;
- hard to run;
- focused on polish over usefulness;
- vague about where the data came from;
- missing explanation of decisions.

That is it.
