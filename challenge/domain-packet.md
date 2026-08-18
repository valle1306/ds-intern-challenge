# Fictional Domain Packet

You are helping a fictional product team that owns **SignalDesk**, an internal tool for AI-assisted workflows.

SignalDesk is used by a few internal teams to speed up repetitive work. The team recently changed some prompts and review policies. They have a small export of workflow usage, but the data is noisy and the definitions are not perfect.

A teammate asks:

> We launched a few AI-assisted workflows for internal teams. Can you help us understand what is working, what looks suspicious, and what we should look at next?

They do **not** need a complete analytics system. They need one small useful artifact that helps them make a better next decision.

## Workflows

- **Lead summary**: helps Sales summarize inbound lead context before follow-up.
- **Reply draft**: helps Support draft responses that a human can edit or approve.
- **Feedback clustering**: helps Product group user feedback into rough themes.

## Terms And Caveats

- `sessions` means workflow runs, not unique users.
- `completed` means the workflow reached a final output, not that the output was good.
- `accepted_output` means a user accepted the output with no major rework. It is a rough signal, not a perfect quality label.
- `flagged_for_review` means a user or policy marked the output for human review. More flags can mean worse output, stricter review, or more careful users.
- `avg_minutes_saved` is an estimate. Treat it as directional, not ground truth.
- `median_confidence` is model-reported confidence. It is not the same as correctness.
- `notes` may change how a row should be interpreted.

## What The Team Cares About

They are trying to decide things like:

- Which workflow seems most useful right now?
- Which metric should they trust least?
- Did a change appear to help, hurt, or create uncertainty?
- What should they investigate before rolling this out more broadly?
- What would be a simple weekly health check for this product area?

You do not need to answer all of these. Pick one useful angle and build around it.

## What To Avoid

- Do not assume model confidence means quality.
- Do not average everything together without thinking about comparability.
- Do not turn this into a large BI project.
- Do not spend time making the artifact fancy if the core judgment is unclear.
