# AI Collaboration Note

## Did You Use AI?

Yes, throughout — exploration, planning, and implementation.

## How You Used It

Used AI to read the domain packet and CSV, design the cleaning and issue-detection logic, draft the Streamlit layout, and write this documentation.

## One Prompt, Workflow, Or Moment That Helped

Asking it to systematically diff the raw file against a cleaned version — duplicate rows, non-numeric literals, missing cells, label-casing groups, and the full expected date × team × workflow × source grid — instead of eyeballing the CSV by hand. This caught issues faster and more completely than manual scanning.

## One Thing You Verified Or Decided Yourself

An earlier AI-assisted pass claimed only one row was missing on 2026-08-07 (Sales/manual). I independently re-verified against the live CSV by diffing the full expected (date × team × workflow × source) grid and found a second missing row (Support/manual) that had been missed — corrected before it shipped. I also independently chose `completed` (not `sessions`) as the denominator for both acceptance and flag rate, after checking that `flagged_for_review <= completed` holds for every row in the data, which is not something to take on faith.

The bigger judgment call was the prompt-change analysis. A naive before/after around the 2026-08-04 change is what an unguided pass produces, and it reports a +4.4pp completion win for Lead summary. That number is almost entirely one duplicated demo-account row the same pipeline had already flagged as high-severity. Deciding to recompute the comparison with high-severity rows excluded — and to publish both columns side by side rather than silently picking the adjusted one — was mine, and it inverts the headline.
