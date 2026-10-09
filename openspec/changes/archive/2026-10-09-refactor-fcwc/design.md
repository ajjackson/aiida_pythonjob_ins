# Design: Compose `ForceConstantsWorkChain` into the force-constants workflows

## Context

After `migrate-castep-reader-to-calcfunction`, `workflows/base.py` holds:

- `ForceConstantsWorkChain`: an abstract base with no outline. It declares `castep_file`, `force_constants`, `code` and `options`, the "exactly one source" validator, exit codes 400 and 410 (`ERROR_READ_FAILED`), `get_job_metadata()`, and a `resolve_force_constants` step that calls the in-process CASTEP read calcfunction.
- `DispersionWorkChain`, `DosWorkChain` and `ToscaFromForceConstantsWorkChain` subclass it and begin their outlines with `cls.resolve_force_constants`.
- `ToscaFromModesWorkChain` subclasses `WorkChain` and duplicates `code`, `options`, `get_job_metadata()` and exit code 400.

## Goals / Non-Goals

**Goals:** a launchable source-resolution unit whose internal steps can change without touching its consumers; no duplicated source or dispatch code; validators that cannot overwrite each other.

**Non-Goals:** see proposal.md. Design-level additions: no change to the read calcfunction's behaviour, and no new outputs on the consuming workflows.

## Decisions

### 1. Compose with `expose_inputs` into a namespace

Consumers call `spec.expose_inputs(ForceConstantsWorkChain, namespace="force_constants")` and submit it as a child.

- This matches AiiDA's guidance that "each workflow should perform exactly one task", with parents wrapping children through exposed ports ([Modular workflow design](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/workflows/usage.html#modular-workflow-design)). It is also how aiida-quantumespresso builds higher-level workflows: `PwBandsWorkChain` and `PdosWorkChain` expose `PwBaseWorkChain` under `scf`/`nscf`/`bands` namespaces ([pw/bands.py](https://github.com/aiidateam/aiida-quantumespresso/blob/main/src/aiida_quantumespresso/workflows/pw/bands.py)). This package already does the same for `ToscaFromModesWorkChain` under `spectrum`.
- The child's outline is private. Steps added for new formats or conversions don't change consumers.
- Plumpy's `PortNamespace.absorb` overwrites the destination namespace's mutable properties, including `validator`, with the source's ([plumpy.ports](https://plumpy.readthedocs.io/en/latest/apidoc/plumpy.ports.html)). In a namespace, the child's "exactly one" validator lands on `force_constants` and checks exactly the child's inputs. A parent's own root validator can't collide with it.
- `force_constants` is a **required** namespace: a consuming workflow can't run without a source. Plumpy skips the validator of an optional namespace that is empty, so being required also guarantees the "exactly one" check runs when no source is given. `absorb` copies `required=True` from the child's root namespace.

*Rejected: inheriting steps (base class or mixin).* A base can share methods but not outline entries. Every multi-step change to source resolution would edit every consumer's outline.

*Rejected: exposing at the root namespace.* That keeps today's input names, but it copies the child's validator onto the parent root. A later parent root validator would then need explicit composition, and a partial root expose (`include=[...]`) would carry a validator that checks ports which weren't exposed.

### 2. Port names: namespace `force_constants`, child ports `castep_file` and `node`

Callers write `force_constants={"castep_file": f}` or `force_constants={"node": fc}`. Future formats add sibling ports (for example a Phonopy folder) under the same rule: one explicit port per format.

`node` is not an AiiDA naming convention. No port in aiida-core or aiida-quantumespresso is named that way; ports usually name the quantity. Inside the `force_constants` namespace, though, it reads as "force constants, already a node".

*Rejected: `force_constants.force_constants`* (stutters). *Rejected: `source.*`* (doesn't say what the source provides).

### 3. Always delegate

Consumers run the child for both source kinds, so every run has exactly one `ForceConstantsWorkChain` child. With `node`, the child returns its input as its output; workflows may return existing nodes ([workflow concepts](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/workflows/concepts.html)).

*Rejected: skipping the child when a node is supplied.* That repeats source logic in the parent and makes the graph's shape depend on the input.

### 4. `ForceConstantsWorkChain` spec (new module `workflows/force_constants.py`)

The read calcfunction moves here from `base.py`.

| Item | Value |
|---|---|
| Inputs | `castep_file` (`SinglefileData`, optional), `node` (`ForceConstantsData`, optional); namespace validator: exactly one |
| Outline | `if_(cls.has_castep_file)(cls.read_castep_file).else_(cls.use_node)`, `cls.finalize`. A future format adds an `elif_` branch and step. |
| `read_castep_file` | `result, node = read_castep_force_constants.run_get_node(...)`; if `not node.is_finished_ok`, call `report` and return `ERROR_READ_FAILED` |
| Output | `force_constants` (`ForceConstantsData`) |
| Exit codes | `410 ERROR_READ_FAILED` (moved from the old base) |

No `code` or `options`: remote or job-based sources are produced upstream by the caller and passed as `node`.

### 5. One abstract base per feature (`workflows/base.py`)

The two features are separate: needing a force-constants source doesn't imply dispatching jobs, or the reverse. Each gets its own abstract base, and consumers inherit the features they use.

```
WorkChain
├── JobDispatchWorkChain           code, options, get_job_metadata(), 400 ERROR_SUB_PROCESS_FAILED
└── FromForceConstantsWorkChain    define(): expose_inputs(ForceConstantsWorkChain, namespace="force_constants")
                                             402 ERROR_SUB_PROCESS_FAILED_FORCE_CONSTANTS
                                   run_force_constants():     submit child with
                                       exposed_inputs(ForceConstantsWorkChain, namespace="force_constants")
                                       → ToContext(force_constants_workchain=...)
                                   inspect_force_constants(): ok → self.ctx.force_constants =
                                                                   child.outputs.force_constants
                                                              else → report + 402

ToscaFromModesWorkChain(JobDispatchWorkChain)                         re-declares 400 with its own message
DispersionWorkChain(FromForceConstantsWorkChain, JobDispatchWorkChain)  outline: run_force_constants,
DosWorkChain(FromForceConstantsWorkChain, JobDispatchWorkChain)                  inspect_force_constants, ...
ToscaFromForceConstantsWorkChain(FromForceConstantsWorkChain, JobDispatchWorkChain)
```

- **Rules:** each base's `define()` calls `super().define(spec)`, so Python's method resolution order builds one spec through every base. Plumpy asserts that the chain reaches `Process.define`. Neither base references the other's ports, methods or exit codes, and neither has an outline.
- **Why the bases subclass `WorkChain` rather than being plain mixins:** each base can build its spec on its own, so it can be tested alone. `Process.spec()` caches `_spec` in the class's own `__dict__`, so building a base's spec doesn't leak into subclasses. The `*WorkChain` names also keep them under the existing autoapi skip, so their step methods stay out of the API reference. Neither base is registered or exported.
- **Exit codes:** they are stored by label (`ProcessSpec.exit_code`), and a subclass's `define()` runs after its bases'. So `ToscaFromModesWorkChain` re-declaring `ERROR_SUB_PROCESS_FAILED` keeps its specific message. The two bases use different labels and numbers, so combining them never collides.
- `_compose_validators` from the earlier plan is not needed: neither base sets a root validator, and Decision 1 keeps the source validator in its namespace.

*Rejected: a linear chain (`FromForceConstantsWorkChain(JobDispatchWorkChain)`).* It works with today's consumers, but it ties two independent features together, forcing `code` and `options` on any future force-constants consumer that doesn't dispatch PythonJobs.

*Rejected: plain mixins that don't subclass `WorkChain`.* Their spec can't be built or tested on its own, and their step methods would appear in the API reference. Spec-free mixins such as aiida-quantumespresso's `ProtocolMixin` don't have these problems, but ours modify the spec.

### 6. Exit codes

| Process | Code | Meaning |
|---|---|---|
| read calcfunction | its `ExitCode` (prerequisite change) | file unreadable |
| `ForceConstantsWorkChain` | 410 `ERROR_READ_FAILED` | the read calcfunction failed |
| consumers | 402 `ERROR_SUB_PROCESS_FAILED_FORCE_CONSTANTS` | the child failed |
| consumers | 400 `ERROR_SUB_PROCESS_FAILED` | a PythonJob failed |
| `ToscaFromForceConstantsWorkChain` | 401 `ERROR_SPECTRUM_WORKCHAIN_FAILED` | unchanged |

Each parent declares one generic code per sub-process. This is the aiida-quantumespresso convention (`PwBandsWorkChain`: `402 ERROR_SUB_PROCESS_FAILED_SCF`, `403 …_BANDS`), and the 401 above already follows it. The specific reason stays on the child node.

*Rejected: passing the child's code through* (`return child.exit_code`). AiiDA accepts it, but the code would be undeclared on the parent, missing from its docs, and could collide with the parent's own numbers.

## Risks / Trade-offs

- [If `force_constants` ever became optional, "neither source" would pass silently (Decision 1).] → The existing "neither source" test and a spec-only `required` assertion (task 2.1) guard it.
- [Each run gains one `WorkChainNode`.] → The cost is small. Workflow nodes are never cached ([caching](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/provenance/caching.html)), but the read calcfunction inside remains cacheable.
- [The input rename breaks callers, including `force_constants=node`, which now hits a namespace and fails with a "not a Mapping" error.] → `CHANGELOG.md`, `README.md`, `workflows.rst` and the tutorials show the new form.
- [Nested inputs link to the parent with labels such as `force_constants__castep_file`.] → Only queries by link label are affected; the child's links keep plain labels.
