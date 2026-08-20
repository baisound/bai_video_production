# TASK-014 — Qwen3-TTS Runtime Artifact Closure Intake R0 Design

Date: `2026-08-21`
Status: `JUDGE_ACCEPTED / DESIGN_FROZEN / NETWORK_METADATA_BLOCKED / ARTIFACT_DOWNLOAD_BLOCKED / UNCOMMITTED`
Development depth: `DEV-4 FOUNDATION CRITICAL`
Base: `main@ee127241c7dfc03efb3008f351a33498506a6f57`

## 1. Goal and boundary

This design defines the next two-stage intake that will eventually supply a
complete accepted input to the merged
`bai.task014.qwen3-tts-runtime-artifact-manifest.v1` compiler.

It does not accept a manifest, download an artifact body, create or mutate a
runtime, execute target Python, import a package, inspect model bodies, read
Owner audio, load a model, run inference or invoke ffmpeg/ffprobe/SoX.

The fixed target remains:

```text
WINDOWS / win_amd64 / cp312 / Python 3.12.4
qwen-tts 0.1.1
torch 2.11.0+cu130
torchaudio 2.11.0+cu130
transformers 4.57.3
accelerate 1.12.0
SDPA (FlashAttention excluded)
```

No fallback matrix, installed-tree self-hash, package-version claim, pip
report, cache object or community wheel can replace an accepted retained
artifact coordinate.

## 2. Current facts

Merged AU2C2A records only a bounded feasibility observation:

- the Qwen wheel candidate matches the merged exact pin;
- the retained Python installer is a candidate whose official coordinate is
  not yet bound;
- a compatible installed runtime candidate exists, but its installed files
  and package inventory are not public authority;
- retained-artifact closure, availability and absence remain unconfirmed.

A non-authoritative feasibility note observed during design exploration suggested:

- Python.org still publishes the Python 3.12.4 Windows 64-bit installer;
- the official PyTorch cu130 simple indexes publish cp312/win_amd64
  `torch 2.11.0+cu130` and `torchaudio 2.11.0+cu130` artifacts;
- PyPI exposes the required qwen-tts and Transformers releases;
- FFmpeg.org publishes source only and points Windows users to BtbN and
  gyan.dev binary-build providers;
- BtbN publishes bounded GitHub release assets with release-level hashes;
- SoX 14.4.2 Windows binaries are hosted at SourceForge, which is not admitted
  by the current manifest provider matrix.

That exploration has no accepted request receipt, exact response-body digest or
rebound network Authority artifact in this repository. Its report says that no
artifact body was downloaded, but that report is not independently established.
The entire note is therefore `FEASIBILITY_ONLY / NOT_REPRODUCIBLE /
NOT_CONFIRMED`, not Stage A Evidence. It authenticates no artifact and creates
no future network Authority. Stage A must repeat every required metadata
observation only after its network Authority is separately rebound to the
accepted design.

## 3. Why intake is two-stage

Official indexes can identify a provisional filename, version, byte count and
digest. PEP 658 metadata can help derive dependency edges without installing a
wheel. It cannot supply the exact wheel `RECORD`, full member set or payload
inventory required by the final manifest.

Therefore the flow is strictly split:

```text
Stage A — metadata-only provisional closure plan
  -> independent DEV-4 review and exact accepted plan digest
Stage B — separately authorized exact-file acquisition
  -> verify bytes/SHA before parsing
  -> parse the same held artifact bytes without execution
  -> compile final AU2C1 manifest
  -> independent DEV-4 review
```

Stage A never transitions automatically into Stage B. Stage B never installs
or imports the acquired artifacts.

## 4. Stage A — provisional closure plan

### 4.1 Allowed network surface

Only anonymous HTTPS `GET`/`HEAD` requests with no credentials, cookies,
uploads or redirects outside the admitted host set may be used:

- `www.python.org` / `python.org`;
- `pypi.org` / `files.pythonhosted.org`;
- `download.pytorch.org` and only an exact content-host class admitted by an
  accepted contract revision, reached from a digest-bound simple-index link;
- `ffmpeg.org` for the upstream Windows-provider reference;
- `github.com`, `api.github.com` and the exact GitHub release content hosts for
  a selected BtbN release asset.

SourceForge/native SoX executable acquisition is excluded unless a separate
contract revision admits its provider/provenance. The required Python `sox`
distribution remains part of the active Qwen dependency closure.

Response limits:

- index/JSON/HTML response: maximum 16 MiB each;
- metadata sidecar: maximum 4 MiB each;
- redirects: maximum 3, with scheme and final-host revalidation;
- requests: maximum 512;
- wall-clock: maximum 30 minutes;
- no artifact body response is accepted in Stage A.

Any TLS, status, content-length, digest, filename, marker or host ambiguity is
`UNKNOWN / STOP`.

The current AU2C1 provider matrix admits `download.pytorch.org` but does not
represent a separately bound final content host. Feasibility notes indicate
that simple-index links can use `download-r2.pytorch.org`. Stage A must not hide
that distinction behind redirects. If the artifact cannot be addressed and
fetched entirely under the admitted canonical host, an AU2C1 R1 contract
revision must add an exact final-content coordinate and closed PyTorch
content-host rule before the provisional plan can become a final manifest.

GitHub release acquisition has the same boundary. A canonical query-free
`github.com` or `api.github.com` release/asset coordinate is distinct from a
provider-controlled content URL that may contain expiring query parameters.
Before any BtbN asset is selected, AU2C1 R1 must freeze:

- the exact repository, release and asset identity fields;
- allowed redirect status codes and an exact final-host-class allowlist;
- a maximum of three redirects, HTTPS on every hop and public-DNS-only hosts;
- no credential, cookie or authorization forwarding to a different host;
- revalidation of scheme, host class, content length and filename at every hop;
- a public query-free canonical source coordinate plus a domain-separated
  transport observation digest over safe hop fields;
- non-persistence of query strings, signatures, credentials and response
  bodies in any public or private plan, manifest, receipt, Evidence, log or
  error.

For every initial host and redirect hop, the resolver must resolve all address
records and reject private, reserved, unspecified, loopback, link-local,
multicast and non-global IPv4/IPv6 addresses. The connected peer address must be
obtained from the TLS transport and revalidated against both the resolved set
and the same global-address policy before accepting headers or bytes. DNS
changes, mixed global/non-global answers, missing peer identity, proxy
interposition without an accepted identity, or a peer outside the resolved set
are `UNKNOWN / STOP`. Host and peer checks repeat on every redirect; an accepted
hostname alone is insufficient.

The PyTorch content-host case and GitHub release-content case use this same
canonical-source-versus-effective-transport model. A redirect target or
temporary query is never silently promoted to an official source coordinate.

### 4.2 Root constraints

The provisional solver starts from exact constraints, not the observed
installed set:

- exact merged Qwen wheel pin and its exact nine `Requires-Dist` rows;
- exact `torch==2.11.0+cu130` and `torchaudio==2.11.0+cu130` for
  `cp312-cp312-win_amd64`;
- `python_version=3.12`, `python_full_version=3.12.4`,
  `sys_platform=win32`, `platform_system=Windows`,
  `platform_machine=AMD64`, `implementation_name=cpython`;
- extras disabled in R0;
- FlashAttention absent;
- the exact ffmpeg/ffprobe pair required for normalization and private-audio
  structure checks.

The solver must use a pinned, independently accepted PEP 508/440/tags parser
whose package artifact digest is part of its observer identity. Unsupported
marker, extra, direct-URL, editable or source-build requirements fail closed.
It must not reuse AU2C1's deliberately bounded grammar as a general package
resolver.

Resolution is deterministic and fail closed:

1. normalize every project name and bind one owner index before fetching any
   candidates: `torch` and `torchaudio` use only the accepted PyTorch cu130
   index; ordinary Python distributions use only PyPI; Python and BtbN tools
   use their separately bound project-release providers;
2. reject a project appearing through another provider, an unowned project
   index, source distributions, editable/direct URL requirements and candidate
   records whose normalized identity conflicts;
3. capture the complete bounded candidate set used for each project before
   selection. Each record contains canonical URL, filename, normalized version,
   bytes, SHA-256, yanked state/reason, `Requires-Python`, wheel tags, metadata
   digest and provider/index identity;
4. reject yanked, prerelease and development releases. Stable post releases
   are allowed when constraints select them. Local versions are allowed only
   for the exact pinned `torch==2.11.0+cu130` and
   `torchaudio==2.11.0+cu130` roots;
5. evaluate all accumulated constraints and markers under the one fixed R0
   environment. Conflicting constraints, unsupported markers, active cycles,
   missing candidates or changing candidate snapshots are `CLOSURE_UNKNOWN`;
6. select the highest compatible PEP 440 version, then the first compatible
   wheel tag in the pinned `packaging.tags` order for cp312/win_amd64, then the
   ASCII-byte-smallest filename. A duplicate coordinate with different bytes,
   hash or metadata is `BLOCKED`, never a tie-break;
7. recompute closure until the normalized edge and selected-candidate sets are
   stable. Any new constraint that changes an already selected candidate causes
   a full deterministic recomputation from the frozen candidate snapshots;
8. domain-separate the stable semantic inputs from volatile request
   observations and hash each canonical projection independently as specified
   below. These digests support reproducibility and audit only, not authenticity
   or execution Authority.

The network schedule is deterministic: start with roots sorted by normalized
provider/project identity; process each dependency frontier in ASCII-byte order
of normalized project identity and canonical query-free request URL; and sort
all response-derived records before hashing. Discovery order, response arrival
order and mapping insertion order never enter a digest.

Two domain-separated digests are required. The semantic plan digest contains
only canonical provider/project coordinates, safe response-body/candidate-set
digests, fixed resolver environment, constraints, selections and graph, and
excludes `evaluated_at`, request timing, redirect timing, peer addresses and
other volatile transport observations. A separate observation-receipt digest
binds the canonical ordered safe request/hop records and timestamps. Therefore
the same accepted snapshots and resolver inputs reproduce the same semantic
plan digest, while distinct observations remain separately auditable.

`Requires-Python` must admit CPython 3.12.4. Wheel build/tag compatibility is
derived from the filename and WHEEL metadata where available; caller-supplied
tags are never authoritative. The same input snapshots must produce the same
selection and plan digest on every run.

### 4.3 Provisional artifact record

Each selected candidate records:

- normalized distribution or tool identity and exact version;
- provider, query-free official index/release URL and the accepted final-host
  class plus safe content-path digest defined by the provider contract;
- filename, wheel tag, expected bytes and SHA-256;
- metadata URL/hash/bytes and exact `Requires-Dist` rows;
- selected marker environment and evaluation result;
- parent requirement identity and root reachability;
- license declaration and whether manual legal review remains required;
- whether the artifact is already retained at an explicitly supplied public
  path, without persisting that absolute path;
- `availability=RETAINED_MATCH / RETAINED_MISMATCH / MISSING /
  NOT_CONFIRMED` only when the accepted bounded inventory procedure supports
  that state.

The plan has a domain-separated canonical digest. It is diagnostic and carries
fixed false authority fields for capability, install, import, runtime reuse,
model load and consumer execution.

Every metadata request observation additionally records `evaluated_at` in UTC,
observer/tool id, revision and digest, exact query-free canonical request URL,
method, status, content type, declared/observed bytes, redirect count,
final-host class, safe content-path digest, response-body SHA-256 and parsed
candidate/result count. Public Evidence retains only bounded counts, canonical
public coordinates and domain-separated response or candidate-set digests.
Private task Evidence may retain the same safe fields, connected-peer policy
result and timing, but never raw response bodies, redirect queries, signatures,
credentials or complete effective URLs. Missing or incomplete observation
fields make the plan `NOT_CONFIRMED`.

### 4.4 Retained inventory observation

The inventory observer receives an exact explicit public artifact root and the
plan's exact filenames. It does not scan a drive or shared cache. It must:

- require a fixed local Windows volume before filesystem I/O;
- reject UNC/device/removable/reparse/escape/case-collision paths;
- enumerate only the exact supplied task-owned root with bounded entries;
- open and hash files streaming with pre/open/post identity checks;
- report unreadable/race/extra/missing/mismatch separately;
- redact absolute paths and file identities from the public projection;
- remain diagnostic, non-capability and post-return non-authoritative.

Only this accepted observer may classify a planned artifact as retained or
missing. AU2C2A's first-level feasibility listing is not reused as absence
Evidence.

## 5. Native tool policy

### 5.1 ffmpeg/ffprobe

FFmpeg.org supplies source and identifies BtbN as a Windows binary-build
provider. R0 may select one exact hash-pinned BtbN GitHub release candidate only
when the
plan binds:

- exact GitHub repository id, release id/tag and asset id;
- exact release tag and upstream FFmpeg commit/version;
- exact static win64 archive filename, bytes and release SHA-256;
- checksum-asset identity, provenance and the limitation that a
  publisher-controlled release/checksum can be replaced until acquired bytes
  independently match the accepted hash;
- BtbN build project identity, exact build configuration and legal/license
  review result;
- exact member paths and hashes for `ffmpeg.exe` and `ffprobe.exe` after the
  acquired archive itself passes its expected SHA-256;
- the two tools to the same archive and build receipt.

`provider=OFFICIAL_PROJECT_RELEASE` then means the official release of the
named BtbN build project, not an upstream-produced FFmpeg binary. Evidence must
not relabel it as an official FFmpeg.org executable.

The TASK-037 Chocolatey `ffmpeg 8.1.2` nupkg hash is CI supply Evidence only.
It is not selected for TASK-014 because a package-object hash alone does not
prove the final executable bytes or prohibit install-script network behavior.

### 5.2 SoX

The Python `sox` distribution is one of Qwen's active requirements and is never
removed from the Python distribution closure. Only the native SoX executable
and tool artifact are optional in the merged manifest contract.

Stage A has metadata only and therefore records native SoX as
`SOX_EXECUTABLE_REQUIREMENT_UNKNOWN`. After the exact selected wheel bodies are
acquired, Stage B may perform a no-import/no-execution reachable-source review
from the admitted tuple-based `generate_voice_clone` entry path. It may record
`NOT_REQUIRED` only when every reachable call and dynamic import/process edge is
resolved and none can invoke a SoX executable. Dynamic lookup, plugin dispatch,
unresolved import, conditional code or process construction is `UNKNOWN / STOP`.
If a native SoX executable is required, Stage B stops because SourceForge is not
admitted by AU2C1; a separate provider/provenance contract revision and
legal/security review is mandatory before any native SoX artifact acquisition.

No PATH or process-local executable discovery may answer this decision.

## 6. Stage B — exact acquisition and same-handle parsing

Stage B is ineligible until Stage A's exact plan is Judge-accepted and network
download authority is rebound to that plan digest.

The acquisition unit must:

1. validate the fixed local volume and open every approved ancestor and the
   task parent top-down with non-inheritable, no-follow handles; reject remote,
   removable, device, reparse, final-path, containment or stable-file-id
   mismatch before creating anything;
2. require absent staging and final names, create the staging directory and
   artifact with handle-relative/create-new semantics, and never overwrite a
   retained artifact;
3. hold an exclusive non-inheritable artifact handle and stream the one bounded
   HTTPS response directly to that handle while computing bytes and SHA-256;
4. flush with `FlushFileBuffers`, verify expected size/hash and file identity,
   then seek/read and parse through the same held handle (or its bounded
   handle-backed reader), never by reopening the path;
5. validate wheel METADATA/WHEEL/RECORD or tool archive members, safe names,
   tags, hashes, sizes, duplicates, encryption/compression and case collisions;
6. apply the protected task-owned DACL through the held object, read back exact
   protection/allowlist semantics and treat the read-only attribute only as a
   UX hint, never as immutability;
7. atomically rename by handle on the same volume with no-replace semantics,
   retain parent and file handles, re-enumerate the exact final name and rehash
   through the same handle after finalization;
8. preserve mismatch or ambiguous state as an exact recovery-required object,
   with no delete, overwrite or blind retry;
9. derive the final dependency graph, runtime file mappings and native-library
   ownership from the exact held artifacts;
10. compile the merged AU2C1 manifest and require schema/parser parity;
11. close handles in reverse order, retain and retry any failed close, and issue
   only a diagnostic receipt that truthfully records opened/read/verified/
   finalized phases and any unreleased-handle count.

Create-new, a path hash or an ACL alone does not make bytes immutable. The only
accepted parsing boundary is the same live held handle and stable identity.
After the session closes, even a successful receipt remains non-capability,
does not guarantee post-return state and cannot authorize install, import or
reuse; every later consumer must freshly revalidate under its own accepted live
session.

No pip, installer, extraction-to-runtime, target Python, import, model or audio
operation occurs in Stage B. Runtime construction/verification is a later
Atomic Unit after the final manifest is independently accepted.

## 7. Failure and recovery

- unavailable official coordinate: `ARTIFACT_COORDINATE_UNAVAILABLE / BLOCKED`;
- metadata graph ambiguity or unsupported requirement: `CLOSURE_UNKNOWN`;
- retained inventory mismatch: `RETAINED_MISMATCH`, never automatic delete;
- confirmed missing artifact: `RETAINED_ARTIFACT_MISSING`, eligible only for a
  separately authorized Stage B plan entry;
- downloaded size/hash mismatch: preserve task staging, `BLOCKED`, no retry;
- post-request ambiguity: `UNKNOWN`, no blind replay;
- provider/source contract mismatch: stop; do not switch provider or matrix.

Recovery never deletes a shared cache, installed environment, model snapshot,
Owner media or earlier retained artifact. Any cleanup is a separate exact-path
destructive action.

## 8. Verification floor

Stage A implementation must cover:

- strict official host/redirect/content-type/size/request/time limits;
- per-hop DNS and connected-peer global-address checks, including rebinding,
  mixed/private/reserved/loopback/link-local/IPv6/proxy failure cases;
- PEP 508/440 active closure, cycles, missing/extra/orphan distributions,
  multiple marker rows and unsupported extras/direct URLs/source builds;
- cp312/win_amd64 and cu130 torch/torchaudio coupling;
- metadata digest/body mismatch and dependency-confusion cases;
- bounded retained inventory missing/extra/race/reparse/access classifications;
- BtbN release/project/upstream/build distinction and same-archive tool pair;
- Stage A native-SoX `UNKNOWN` truthfulness and Stage B reachable-source
  required/not-required fail-closed decision;
- canonical plan digest, public redaction and all authority/effect flags;
- static absence of artifact-body download, install, subprocess, package
  import, model/audio and filesystem mutation from the metadata solver.

Stage B adds archive/adversarial parsing, download truncation/mismatch,
create-new containment, recovery and exact manifest compilation tests. Native
fault coverage must include ancestor/file reparse and identity swap, rename or
replacement between write/hash/parse, mutation during same-handle parsing,
short write, flush failure, ACL apply/readback mismatch, cross-volume or
existing-target rename, post-final rehash mismatch and close failure/retry.

## 9. Atomic Unit split and current verdict

Recommended split:

1. `AU2C2B1` — metadata-only provisional closure solver, schema/mirror/tests and
   Evidence; official metadata network execution only after design acceptance;
2. `AU2C2B2` — bounded retained-inventory observer and diagnostic receipt;
3. `AU2C2B3` — plan review/freeze with exact selected coordinates;
4. `AU2C2C` — separately authorized exact artifact acquisition and held-byte
   parser/final AU2C1 manifest compilation;
5. later runtime construction and offline aggregate verifier AUs.

Any required AU2C1 R1 source-coordinate extension is inserted before B3 and
must be independently reviewed; B1 cannot self-authorize a broader provider
or redirect host.

Current verdict:

- independent Tester: `PASS / C0 H0 M0`;
- independent Critic/Judge: `PASS / C0 H0 M0`;
- design review: `JUDGE_ACCEPTED / DESIGN_FROZEN`;
- metadata feasibility note: `NOT_CONFIRMED / NOT_REPRODUCIBLE`;
- Stage A implementation: `NOT_STARTED`;
- actual Stage A metadata network observation: `BLOCKED / AUTHORITY_REBIND_REQUIRED`;
- artifact body download/install/runtime execution: `BLOCKED`;
- model load/Owner audio/inference/native audio effect: `BLOCKED`.

## 10. References

- merged AU2C1 manifest contract and Evidence;
- merged AU2C2A retained-artifact availability audit;
- frozen TASK-014 local preview runbook;
- TASK-037 R2 hosted FFmpeg supply Evidence;
- Python 3.12.4 release page;
- PyPI JSON/simple APIs;
- PyTorch cu130 simple indexes;
- FFmpeg Windows download-provider page;
- BtbN FFmpeg-Builds releases;
- exact merged Qwen wheel/locked-session contracts.
