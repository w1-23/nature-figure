# Figure checks

## Ordinary SVG

- Verify data, grouping, raw values, transformations, units and summary definitions. At the final physical size, check readable labels, visible data and legends, canvas bounds, tick spacing and comparable panel alignment.
- The example measures label bounds, tick overlap and actual panel rectangles. Inspect the exported figure and each panel before claiming visual review. Validate the SVG and store its hash with the frozen source, renderer, object IDs and revision.
- Record PDF text and collision audits as `not_requested` for ordinary SVG. The upstream workflow audited PDF after every revision. The adapted workflow runs ordinary SVG checks and reserves PDF-specific tests for a requested PDF audit or submission review.

## Submission PDF on demand

Confirm the journal, article type and submission stage. Verify current official requirements for dimensions, text and stroke size, output format, legend and source data. Flagship Nature and Nature Machine Intelligence requirements can differ. Historical examples do not establish current policy.

Export from the same frozen revision and audit that exact PDF. The following sample uses the separately provisioned PDF QA runtime. Its `5` pt minimum is a fixture threshold. Apply the confirmed threshold for a submission.

```bash
python scripts/grouped_example.py render "$out/frozen.json" "$out/submission" means \
  --format pdf --pdf-qa-min-pt 5
```

Review `review_required` at final size. Repair `fail` before submitting. For `not_auditable`, report the missing capability. Human visual and scientific checks, legend review and journal eligibility remain separate.
