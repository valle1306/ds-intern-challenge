# Sample Data

`product_usage_events.csv` is fictional and intentionally messy. It is provided for Track A of the challenge.

Before using it, read the fictional domain context in [../challenge/domain-packet.md](../challenge/domain-packet.md).

Each row is a daily summary for a workflow inside a fictional product.

Fields:

- `date`: observation date
- `team`: fictional internal team using the workflow
- `workflow`: AI-assisted workflow name
- `source`: how usage was triggered
- `sessions`: number of workflow sessions
- `completed`: number of sessions completed
- `accepted_output`: number of outputs accepted by a user
- `flagged_for_review`: number of outputs flagged for review
- `avg_minutes_saved`: estimated average minutes saved per completed session
- `median_confidence`: model confidence-like value from 0 to 1, when available
- `user_rating`: optional user rating from 1 to 5
- `notes`: experiment or data-quality context

Some values are missing, inconsistent, duplicated, or suspicious by design.
