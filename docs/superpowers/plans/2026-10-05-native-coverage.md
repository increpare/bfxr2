# Native coverage expansion plan

Execute inline in the existing isolated worktree.

1. Generate four immutable 8,192-row Transfxr shards using existing
   `neural_invert.data.generate_dataset`, with seeds 20261020 through 20261023,
   four separate workers and one computational thread per worker. Save runner
   and source hashes/status; stop on a failed worker rather than silently retry.
2. Check completeness, control/schema/feature hashes, canonical replay samples,
   silence/failure counts and duplicate groups. Freeze evaluation probes before
   incorporating the generated rows into training.
3. Build a new derivative dataset preserving original splits and normalization.
   Test exclusion of original validation/probe controls and atomic completion.
   Update the controlled training recipe only after verifying actual shard counts.
4. Train matched old/expanded-data experts from the same frozen v3 checkpoint,
   controlling optimizer update count, normalization and stratum mass. Report
   native and structured validation separately and retain checkpoints/history.
5. Render equal-budget development and fresh holdout comparisons, then prepare
   a short new listening batch only if candidate generation merits human review.
