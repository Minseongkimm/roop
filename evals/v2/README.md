# Roop eval v2

Ten realistic feature tasks on one shared inventory-service fixture
(`fixture/src`, stdlib only). Hidden unittest files live under
`golden/tests/` and must not be shown to the model. Reference overlays
live under `reference/<task-id>/src/` (only files that differ from the
fixture). Trivial stubs used for test sanity checks live under
`stubs/<task-id>/src/`.

## Tasks

Single-file: `item-validate`, `config-parser`, `cli-format`,
`item-search`, `csv-export`.

Multi-file: `category-crud`, `list-pagination`, `audit-log`,
`soft-delete`, `place-order`.

All ten are in the `heldout` split. `difficulty` is `single` or `multi`.

## Harness

The manifest matches v1 (`id`, `title`, `description`, `allow_paths`,
`acceptance_criteria`, `verify_command`, `protected_globs`,
`golden_test`, `split`, `src_files`) plus a suite-level `fixture`
field. `load_suite` reads that field. `install_fixture` copies
`evals/v2/fixture` (skipping any `tests/`) into the scratch workspace
before golden tests are installed. `run_compare` and `enqueue_suite`
do this automatically. v1 suites omit `fixture`, so their scratch
`src/` stays empty.

Reference overlays must be applied on top of the fixture when scoring
a known solution; they are not a complete tree by themselves.

Run one task's hidden tests after materializing fixture + overlay:

```
python3 -m unittest discover -s tests -p test_<id>.py -v
```
