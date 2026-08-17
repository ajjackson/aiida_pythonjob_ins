## Context

See proposal.md for motivation. This document records the architecture and the
decisions that produced the behaviour now specified in `specs/`, rather than
proposing a new design: every decision below is already implemented.

Two existing documents overlap with this one and remain the primary sources for
their respective material:

- `docs/source/design_notes.rst` - the reader-facing write-up of what the
  `aiida-pythonjob` execution model implies for plugin authors (process-type
  constraints, the serializer architecture, pickling modes, pytest setup). It is
  published as part of the documentation. This design doc references it instead
  of duplicating it.
- `PLAN.md` - the pre-OpenSpec planning document, deleted by this change and now
  recoverable only from git history. Section numbers cited below refer to it as it
  stood at that point. It had already drifted from the code in at least one place
  (its §6 described the aarch64 wheel workaround as a `[tool.uv.sources]` entry
  with a platform marker, while the implementation had moved to
  `[tool.uv] find-links`), which is itself the argument for retiring it in favour
  of specs that are validated.

Constraints that shaped everything else:

- A `PythonJob` function runs in a separate interpreter with no AiiDA profile. It
  can neither construct nor return an AiiDA node.
- `aiida-pythonjob` reads AiiDA configuration at *import* time to build its
  serializer registry, so merely importing this package requires a configuration
  to exist.
- Euphonic has no aarch64 Linux wheel on PyPI for 2.x, and aarch64 Linux is one of
  the environments the project is developed on, alongside x86-64 Linux.

## Goals / Non-Goals

**Goals:**

- Put existing scientific packages onto an AiiDA provenance graph, and nothing
  more. This is a wrapper layer.
- Keep the scientific code ordinary, importable Python that can be tested without
  AiiDA and executed in an environment that has never heard of AiiDA.
- Prefer AiiDA's native materials-science types at every boundary where one fits,
  so results are usable by existing AiiDA tooling.
- Make the plugin a readable exemplar of the `aiida-pythonjob` model.

**Non-Goals:**

- Method development, or any scientific implementation of its own. The physics
  belongs to the upstream packages - `euphonic`, `seekpath`, and `abinslib` and
  `resins` in future - where it is tested and validated against scientific
  criteria, independently of AiiDA. Those projects have the domain expertise, the
  reference data and the user community to judge such work; this package has
  none of the three. Anything here that starts to resemble a method, a correction
  or a numerical choice with scientific consequences is a sign that the work is
  in the wrong repository and should be contributed upstream instead. The
  practical test is that every number this package produces should be
  reproducible by calling the upstream library directly, which is exactly what
  the equivalence tests assert.
- Optimising for scale. Correctness and clarity were chosen over performance
  wherever the two conflicted.
- Supporting remote schedulers in practice. The standard `Computer`/`Code` hooks
  are used so remote execution is possible, but only localhost is exercised.

## Decisions

### Python-API execution instead of CLI wrapping

Euphonic ships a command-line interface, so the conventional AiiDA approach would
be a `CalcJob` plus a `Parser` that writes and reads files. Instead the plugin
runs Euphonic's Python API directly through `aiida-pythonjob`.

*Why:* maintenance. The Python API is the upstream projects' full surface, so a
new capability can be wrapped as soon as it appears there. A CLI wrapper can only
reach what the command line exposes, which means new features must first be given
an argument, an output format and a stable textual contract upstream before this
plugin can use them - and those additions are constrained by what a command line
can reasonably express. The scientific logic also stays as ordinary functions
operating on real objects, rather than being flattened into command-line
arguments and reconstructed from output files.

*Rejected:* `CalcJob` wrapping. Not because a CLI could not in principle carry any
particular quantity - `QpointPhononModes` can be written to a file - but because
each exchanged object would depend on an upstream textual interface existing,
remaining stable, and round-tripping without loss, which is a standing
coordination cost with the upstream projects for no benefit this plugin needs.

### The scientific layer is physically separated from the AiiDA layer

Pure Euphonic functions live in `operations.py`; the process input builders live
in `pythonjobs.py`. The package `__init__` is empty so that importing
`operations` pulls in no AiiDA code.

*Why:* this is what makes by-reference pickling viable against a lean remote
environment, and it lets the science be unit-tested with no profile at all.
*Rejected:* one module per operation containing both the function and its
wrapper, which reads more naturally but would make every remote import drag in
AiiDA. The split is a hard constraint, not a preference: it is asserted by the
spec requirement "Operations are independent of AiiDA".

### Functions are shipped by reference, not by value

`register_pickle_by_value` is left at its default of `False`, so the remote
environment must have this package installed. See `design_notes.rst` for the full
argument.

*Why:* by-value pickling re-serialises the function on every submission and AiiDA
stores that payload per calculation node, so at production scale it inflates
transfer, submission time and the repository. It also cannot help with the heavy
dependency anyway - `cloudpickle` cannot pickle compiled extensions, so Euphonic
must be installed remotely regardless. *Rejected:* by-value as the default, which
the upstream examples use because their functions are defined in `__main__`.

By-value is *not* a supported mode of this package. `register_pickle_by_value`
appears only in a docstring and in `design_notes.rst`; no code sets it and no test
exercises it. Because the builders forward unrecognised keyword arguments to
aiida-pythonjob, a caller could pass it, but nothing here has verified that the
result works. See deferred item 9.

### Custom Data nodes store Euphonic's own JSON in the node repository

`ForceConstantsData`, `QpointPhononModesData` and `EuphonicCrystalData` share a
base that writes the object through Euphonic's public JSON round-trip into the
node's file repository.

*Why:* Euphonic already defines a stable public serialisation, so the plugin does
not invent one. Force-constant arrays are large, and the repository is the part of
AiiDA designed to hold bulk data; putting them in database attributes would bloat
the database and slow queries. *Rejected:* pickling the objects (opaque, version-
fragile) and decomposing them into `ArrayData` (throws away Euphonic's own schema
and has to be maintained against it).

### Native AiiDA types are used wherever one fits

Custom Data types exist only for the two objects with no native equivalent
(force constants, and phonon modes with eigenvectors) plus the crystal bridge.
Everything else uses `StructureData`, `KpointsData`, `BandsData` and `XyData`.

*Why:* `BandsData.show_mpl()` and `export()` then work for free, and other plugins
can consume the results. A `QpointPhononModes` is very nearly `BandsData` plus
eigenvectors, so the band structure is built by *composition* - the eigenvectors
stay in `QpointPhononModesData` and the frequencies are copied into a `BandsData`.
*Rejected:* a custom band-structure type, which would have duplicated `BandsData`
and been invisible to AiiDA's plotting.

### The band path is built parent-side as a calcfunction

`generate_band_path` is a `calcfunction`, not a `PythonJob`, even though seekpath
is a scientific dependency like any other.

*Why:* it must return a `KpointsData`, and a `PythonJob` function cannot construct
a node. The alternative was to return a plain carrier object from a job and
convert it parent-side, which adds a type and a serializer for no benefit; path
generation is cheap, so there is nothing to gain by running it remotely.
*Consequence:* the workflows deliberately mix `PythonJob` steps with
`calcfunction` steps, and the spec pins that split so it is not "tidied up" later.

### Structure extraction is a mixin, not a base-class method

`to_structure()` comes from `CrystalStructureMixin`, applied only to the node
types whose wrapped object carries a crystal.

*Why:* putting it on the shared JSON base would advertise structure extraction on
future types that have no crystal, such as a spectrum collection. *Rejected:*
defining it on the base and raising at runtime for crystal-less types, which moves
a type error to runtime for no gain.

### Conversions are plain functions, not calcfunctions

The functions in `conversions.py` are deliberately undecorated.

*Why:* they are called from three contexts that each preclude the decorator -
inside calcfunctions, inside Data-class methods that must work without an engine,
and on non-node arguments such as a Euphonic `Crystal` or a raw array. Provenance
is recorded one level up by the `calcfunction` and `PythonJob` wrappers that call
them.

### Serializers are passed explicitly, not registered as entry points

The Euphonic-to-node translations are passed to each `prepare_pythonjob_inputs`
call rather than registered through entry points.

*Why:* `aiida-pythonjob` discovers serializers by inspecting `aiida.data`
entry-point names, so registering them that way would mean encoding Python type
paths into entry-point names and risking duplicate-key clashes. Passing them
explicitly keeps one clean entry point per class. *Rejected:* the entry-point tier
(most idiomatic in principle, but collides with the class registrations) and the
config-file tier (machine-local, invisible to collaborators).

### Workflows share a force-constants base with an exclusive-or input

`ForceConstantsWorkChain` resolves force constants from either a CASTEP file or a
prepared node, enforced by an input validator, and both concrete workflows extend
it.

*Why:* the two entry points into every phonon calculation are "I have a calculator
output" and "I already have force constants"; expressing that once avoids
duplicating it per workflow. Reading Phonopy input is deliberately *not* built
into the base: it needs several files, so it is cleaner to read it up front into a
node and pass that. *Rejected:* optional inputs with a runtime check inside the
outline, which would fail later and less clearly than a spec validator.

### Test configuration is redirected before AiiDA is imported

`tests/conftest.py` points `AIIDA_PATH` at a temporary directory and creates a
configuration there at module top, before importing AiiDA.

*Why:* `aiida-pythonjob` calls `get_config()` at import time, so on a machine with
no AiiDA configuration the suite fails during *collection* - before any fixture
can run. Doing it in a fixture is therefore too late. The same trick appears in
`docs/source/conf.py` and the gallery helper for the same reason. *Benefit:* the
session is hermetic either way, so a developer's live installation is never
touched.

### Scientific assertions compare against Euphonic, not against stored numbers

Tests assert that the AiiDA-wrapped result matches a direct public-API call,
within `rtol=1e-3` and `atol=0.05 meV`.

*Why:* golden values would encode one Euphonic version's output and break on
legitimate upstream improvements, while telling us nothing about whether the AiiDA
wrapping is correct - which is the actual subject under test. The tolerance exists
because the two computations run in different processes, where BLAS threading
perturbs near-degenerate acoustic modes.

### Callers supply the Code; the builders' localhost default is a convenience

The WorkChains declare `code` as a required `AbstractCode` input, which is the
idiomatic AiiDA contract: the user creates a code with `verdi code create` and
passes it in. The lower-level input builders additionally default to
`computer="localhost"` with `code=None`, which makes tests and notebooks terse.

*Why this is not specified as a guarantee:* resolving or creating a code from a
bare computer name is aiida-pythonjob's behaviour, not ours - we merely pass the
arguments through. Promising it in our own specification would bind us to the
internals of a pre-1.0 dependency whose API we already pin tightly for that exact
reason. The requirement therefore states only that jobs are directed at a standard
`Computer` and `AbstractCode`, and that workflows demand an explicit code.

### Workflow interfaces are documented from the runtime spec

`workflows.rst` uses AiiDA's `aiida-workchain` directive, and `conf.py` hides
`*WorkChain` classes from AutoAPI.

*Why:* a WorkChain's inputs and outputs are defined at runtime in `define()`, so
AutoAPI can only see the outline-step methods - an implementation detail that
would be presented as if it were the interface. *Known wart:* the AutoAPI tree
consequently omits classes that exist in the source. This is recorded as an open
item rather than resolved here.

### The aarch64 Euphonic wheel is supplied via a local wheel directory

`[tool.uv] find-links = ["wheels"]`, with the wheel gitignored.

*Why:* `find-links` is inert when the directory is absent or empty, so x86-64 CI
resolves from PyPI with no platform marker to maintain, and the workaround
disappears by deleting three lines once upstream publishes aarch64 wheels.
*Rejected:* a `[tool.uv.sources]` entry with a `platform_machine` marker, which was
the original plan and is more explicit, but pins an exact wheel filename in
`pyproject.toml`; and committing the wheel, which would put a large binary in a
repository that never needs it in CI.

## Risks / Trade-offs

- **Euphonic is required in the parent environment**, because the Data classes
  import it at load time and parent-side serialisation builds Euphonic objects
  → accepted; avoiding it would mean lazy imports and exchanging raw arrays across
  the process boundary, losing the typed objects that make the code readable.
- **`cloudpickle` round-trips are sensitive to version skew** between the parent
  and the execution environment → keep the two environments closely matched;
  deriving the remote environment from the project's own lock file is preferred
  over a hand-maintained requirements list.
- **The aarch64 development wheel is a pre-release (2.0.1.dev1) while CI resolves
  2.0.0** → both are 2.x with the same public API, but a difference could surface
  in CI only; revisit if that happens.
- **Python is pinned to exactly 3.12** by that wheel → this constrains every user
  on every platform for the sake of one local workaround, and no code here needs
  3.12; recorded as deferred item 11, and item 12 would remove its cause.
- **A single exit code (400) covers any failed job step** → adequate for a
  proof-of-concept, but a caller cannot distinguish which step failed without
  inspecting the graph.
- **The AutoAPI tree omits WorkChain classes** → readers may not find them where
  they expect; tracked as a follow-up.
- **Documentation and planning text can drift from code**, as PLAN.md §6 already
  had → mitigated by generating what can be generated, and by replacing PLAN.md
  with specs that are validated. Three further instances were found while
  reviewing these specs - `workflows.rst` claiming the workflow pages render exit
  codes, `pythonjobs.py` advertising by-value pickling that nothing exercises, and
  `openspec/config.yaml` still describing PLAN.md in the present tense - so the
  risk is demonstrated rather than hypothetical, and validation covers only the
  specs themselves.

## Migration Plan

No code migration: this change alters no runtime behaviour.

The documentation migration is the point of the change. On archive, the eight
delta specs become `openspec/specs/`. `PLAN.md` itself is deleted rather than
reduced to a pointer: a stub would be a third document to keep current, and the
file remains in git history for anyone needing an original wording. Every
reference to it - two in `README.md`, one in `pyproject.toml`, one each in
`pythonjobs.py` and `serialization.py` - was repointed at the destination below,
citing named sections of `design_notes.rst` rather than section numbers, since
numbered references are what rotted invisibly. Material moves as follows:

| PLAN.md section | Destination |
|---|---|
| §0 reference links, §1 goals and out-of-scope list | `README.md` |
| §1 goals, §9/§10 milestone outcomes | the capability specs |
| §3 architecture, §3.5-§3.7 execution and conversion model | this design doc and `docs/source/design_notes.rst` |
| §2 dependency policy, §5 entry points, §6 wheel | `plugin-packaging` spec |
| §7 testing, §8 CI | `testing-and-ci` spec |
| §10 "implementation notes / decisions made" | this design doc |
| §11 resolved open items | dropped (superseded by the specs) |
| §12 open investigations | future changes; summarised below |

## Open Questions

None affecting this baseline. Everything below is deferred work with a known
shape, not an unresolved decision.

## Deferred work

The consolidated list of follow-ups, each to become its own change proposed
against these specs. Recorded here so they are not scattered across the proposal,
the task list and the planning document this change deletes. The `PLAN.md`
section numbers below record where each item originated.

1. **Audit the entry points and use factories in the documentation.** (Addressed by the `reconcile-documentation-gaps` change). Would
   exercise `plugin-packaging`'s discovery requirements from the outside, which
   nothing currently does. Decided: use factories prominently in the docs, stating
   the equivalent direct import once. (PLAN.md §12.1)
2. **Generate the workflows page from the registered entry points** so it cannot
   drift as workflows are added. Decided: prefer a build-time hook in `conf.py`
   over a custom directive. (PLAN.md §12.2)
3. **Reconcile the omission of WorkChain classes from the AutoAPI tree** with the
   fact that they exist in the source. Explicitly deferred. (PLAN.md §12.3)
4. **Add `abinslib` and then `resins` wrappers** as new operations, data types and
   workflows, reusing the PythonJob and Data-type patterns. The largest item, and
   the reason the package is named generically. (PLAN.md §9.7)
5. **Wire ruff into the main CI workflow** (Addressed by the `setup-ruff-and-relax-python` change), which currently runs pytest only. Note
   that `ruff check` is clean but `ruff format --check` is not: it would reflow
   hand-aligned comments in a README example block, so that must be settled as
   part of the change.
6. **Strengthen the tests to assert what the specs require.** Four gaps, all found
   while reviewing this baseline, none indicating anything broken - the coverage
   simply does not match the contract:

   - *Round-trip fidelity.* The specs require every field and its units to survive
     storage, while the tests check atom count and lattice for crystals, and
     frequencies but not eigenvectors, q-points or weights for phonon modes.
     Nothing checks that a stored node reconstructs without its original input
     file.
   - *Scientific validity.* The specs require a density of states to integrate to
     three modes per atom, and the acoustic branches to vanish at the zone centre
     under the acoustic sum rule. The tests assert only array shapes and
     non-negativity, which an empty or all-zero result would satisfy. Both
     invariants were verified by hand against quartz and NaCl while writing the
     specs; neither is enforced by a test. A density-of-states equivalence test
     against a direct Euphonic call is also missing, though dispersion and
     interpolation have one.
   - *Imaginary-mode handling.* The specs require imaginary frequencies, carried as
     negative values, to survive interpolation and band-structure composition
     unclipped. Nothing tests this. Both bundled materials are dynamically stable,
     so their only negative frequencies are numerical noise of order 1e-3 meV at
     the zone centre; testing the contract meaningfully would need a fixture with
     genuine soft modes.
   - *Entry-point registration.* (Addressed by the `test-entry-point-registration` change). The `plugin-packaging` specs require each class to
     load from the standard plugin factory under its documented name, and no test
     does so; every test imports the classes directly. Add one test per registered
     class asserting `DataFactory`/`WorkflowFactory` returns it for its documented
     entry-point name, which exercises the registration pipeline end to end -
     declaration in `pyproject.toml`, installation into the environment, and
     resolution by AiiDA - rather than any one link in it.

     What existing coverage does and does not reach was established empirically
     rather than assumed. AiiDA refuses to store a `Data` subclass lacking an entry
     point (`StoringNotAllowed`), so tests that store a node already prove *some*
     registration exists; and `node_type` is derived from the entry-point string,
     so the name is embedded in stored data. But `Process.build_process_type`
     takes the opposite policy - on a missing entry point it silently falls back to
     the fully qualified class path - so the two WorkChain entry points could be
     deleted outright with the suite still green. Nor does storing check the
     *name*: renaming an entry point would keep every test passing while breaking
     `DataFactory` for users and changing `node_type` for stored data. Both holes
     close with the same small test, and a per-class test keeps the check honest
     as classes are added.
7. **Defect: the generated density-of-states energy axis clips at zero.** (Addressed by the `dos-clipping` change). The axis
   is built as `arange(0.0, emax + energy_spacing, energy_spacing)`, so imaginary
   modes - conventionally represented as negative frequencies - fall below it and
   contribute no weight, with nothing to indicate their absence. There is currently
   no way for a caller to override this: neither the operation, the input builder
   nor the WorkChain exposes an energy range, only a bin width and unit.

   The governing domain rule, confirmed with the maintainer: an *automatically
   generated* range must span the whole computed dataset and must not clip at zero,
   while an *explicitly supplied* range must be respected exactly as given. The
   present behaviour breaks the first half of that rule.

   Measured on quartz the cost is one mode in 729, the sum reading 2.9959 against
   an exact 3.0000 once the bins are extended below zero - invisible for a stable
   structure. For a dynamically unstable one it would silently understate the
   instability, while the band structure for that same material would show it: the
   same calculation telling the user two different stories.

   A change fixing this would extend the generated axis to cover the full frequency
   range, plausibly add an explicit range input, and carry `MODIFIED` requirements
   against `phonon-operations` (and `phonon-workflows` if an input is added). Its
   sum-rule tests must integrate across the whole data range, so the expected result
   is an exact three modes per atom rather than the truncated 2.9959 seen today.
   Found while reviewing this baseline.

   Worth noting against the wrapper-layer non-goal above: the axis is generated
   here rather than by Euphonic, which is why this package is in a position to get
   it wrong at all. Whether the range construction belongs upstream is a fair
   question for that change to ask.

8. **Surface workflow exit codes in the documentation, and correct the claim that
   they already are.** (Addressed by the `reconcile-documentation-gaps` change). The `aiida-workchain` directive renders inputs, outputs and
   the outline, but not exit codes: `ERROR_SUB_PROCESS_FAILED` appears nowhere in
   the built site except the viewcode source listing. Meanwhile
   `docs/source/workflows.rst` tells the reader these pages "show the real inputs,
   outputs, exit codes and outline", which is inaccurate. Exit codes are part of a
   WorkChain's public contract - a caller switches on them - so they should be
   documented somewhere. Either way the prose needs fixing. Found by building the
   docs while verifying this baseline.

9. **Either exercise pickle-by-value or stop advertising it.** (Addressed by the `reconcile-documentation-gaps` change). The docstring in
   `pythonjobs.py` invites callers to pass `register_pickle_by_value=True` to avoid
   installing this package remotely, while `design_notes.rst` says to "always" use
   the by-reference default. Nothing sets the flag and no test covers it, so the
   suggestion is untested and may not work at all - the operations module imports
   euphonic, numpy and seekpath at module scope, and cloudpickle cannot ship
   compiled extensions by value, so the remote still needs the scientific stack.
   Resolve by testing it against a package-free environment or by removing the
   suggestion, and reconcile the two documents either way. Found while reviewing
   this baseline.

10. **Document running the plugin against a remote Code (SSH plus Slurm).** This is
   the only follow-up that tests a claim the specs already make: both
   `pythonjob-execution` and `phonon-workflows` require that heavy steps are
   dispatchable to a `Computer` "without modification", and nothing verifies it -
   every test and every tutorial runs on localhost. Such a change would need to
   cover provisioning the remote environment, since by-reference pickling requires
   this package to be importable there, and to address the parent/remote version
   skew risk noted above.

   It also collides with an existing requirement: the `documentation` capability
   requires worked examples to be executed at build time, which a cluster example
   cannot be. That change would therefore need to modify the `documentation` spec
   to admit a non-executed guide alongside the executed gallery - which is exactly
   the kind of deliberate, visible spec change this baseline exists to make
   possible.

   Direction already agreed: verify against a throwaway container running SSH,
   Slurm and Python, driven by a dedicated CI workflow, and document it as a
   standalone page. Deliberately *not* part of the routine pytest run or the
   executed gallery, both of which must stay runnable on a laptop with no
   infrastructure - a constraint the `testing-and-ci` capability already requires
   and which this work must not erode.

11. **Drop the exact Python 3.12 pin.** (Addressed by the `setup-ruff-and-relax-python` change) `requires-python = "==3.12.*"` is not a
    language requirement of this package - nothing here uses a 3.12-only feature,
    and the code would run unchanged on 3.11 or 3.13. It exists solely because the
    locally supplied aarch64 Euphonic wheel is built for one interpreter version,
    and an exact pin was the blunt way to stop uv resolving an environment the
    wheel could not satisfy. The cost is borne by every user on every platform,
    including the x86-64 majority who install Euphonic from PyPI and never needed
    the constraint. Replace it with a range reflecting what the package and its
    dependencies actually support, and confine the wheel's interpreter constraint
    to the local aarch64 workaround. Doing so makes the CI matrix a real choice
    rather than a foregone conclusion, and item 12 (aarch64 wheels reaching PyPI)
    would remove the underlying cause entirely. Found while reviewing this
    baseline.

12. **Remove the local wheel workaround once Euphonic publishes aarch64 wheels.**
    `[tool.uv] find-links = ["wheels"]` exists only because PyPI carries no
    aarch64 Linux wheel for Euphonic 2.x, which forces developers on that
    platform to obtain and place one by hand. When upstream publishes, delete the
    `[tool.uv]` block, the `wheels/` directory and its `.gitignore` entry, and the
    README section describing the manual step; then remove the corresponding
    scenarios from `plugin-packaging`. This also clears the way for item 11, since
    the interpreter pin exists only to keep resolution compatible with that wheel,
    and it makes a multi-platform CI matrix cheap. Recorded during this baseline
    as the follow-up the packaging decision already anticipated.
