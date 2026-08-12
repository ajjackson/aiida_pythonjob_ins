## 1. Add the registration tests

- [ ] 1.1 Add a test module covering plugin registration, with one parametrised
      case per registered class pairing its documented entry-point name with the
      class the factory must return.
- [ ] 1.2 Cover the data types through AiiDA's data factory, asserting the
      returned object is the expected class rather than merely resolving.
- [ ] 1.3 Cover the workflows through AiiDA's workflow factory, on the same
      pattern. These are the cases with no existing coverage at all, since a
      missing workflow entry point does not raise - it falls back to the class
      path.
- [ ] 1.4 Note in the module docstring that entry-point metadata is written at
      install time, so a stale editable install can make these tests pass or fail
      independently of `pyproject.toml`.

## 2. Verify the tests can fail

- [ ] 2.1 Temporarily rename one data entry point in `pyproject.toml`, reinstall,
      and confirm the corresponding case fails while the rest of the suite stays
      green; restore afterwards.
- [ ] 2.2 Repeat for one workflow entry point by removing it, confirming the case
      fails - this is the hole that motivated the change, so verify it directly
      rather than assuming symmetry with the data case.
- [ ] 2.3 Confirm the checks need no profile, stored node or submitted job, as the
      spec requires.

## 3. Close out

- [ ] 3.1 Run the full suite and `ruff check`; confirm no regression and no
      measurable increase in runtime.
- [ ] 3.2 Mark the entry-point sub-item of `document-poc-baseline` design item 6
      as addressed by this change, leaving the other three gaps deferred.
- [ ] 3.3 Archive this change after `document-poc-baseline` is archived, since the
      `testing-and-ci` main spec must exist first; then commit from the host,
      which has the git credentials the container lacks.
