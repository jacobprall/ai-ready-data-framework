# Factor 4: Correlated [draft]

**Definition:** Correlated data is traceable from its source to every decision it informs.

## Why It Matters

When AI fails, you need to trace why. Without lineage, debugging is guesswork and accountability is impossible. If a model makes a bad decision, you need to know: What data informed it? Where did that data come from? What transformations did it undergo? Without answers, you can't fix the problem or prevent recurrence.

## Requirements

- End-to-end data lineage from source systems to AI outputs
- Ability to trace any prediction back to the data that informed it
- Audit logs for data transformations
- Versioned datasets for point-in-time reproducibility

## Key Questions

- Can you reproduce a model's output from last month with the exact data it used?
- If a prediction is wrong, how long does it take to identify the root cause?
- Do you have lineage across both batch and real-time paths?
