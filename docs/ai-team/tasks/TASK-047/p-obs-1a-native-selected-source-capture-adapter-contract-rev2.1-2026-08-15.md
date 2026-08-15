# TASK-047 / P-OBS-1A Native Selected-Source Capture Adapter Contract Rev.2.1

- Contract ID: `TASK047-P-OBS-1A-OBS32.2.1-WIN-X64-REV2.1`
- Authority: `DESIGN_CONTRACT_ONLY`
- Implementation / Build / Install / Load / OBS Launch / Capture: `NOT_AUTHORIZED`
- Audio / Device / Asset / Dataset mutation: `NOT_AUTHORIZED`
- Canonical activation: this file is authoritative only when its provenance is
  valid and the exact file is read from `main`.
- Final design finding: Critical / High / Medium = `0 / 0 / 0`

This is the consolidated A-U contract. Earlier drafts and deltas are provenance
inputs, not parallel normative documents. If a dependency is absent or a fact
is unknown, this contract preserves that state and fails closed.

## Precedence

Owner invariants cannot be weakened. The Rev.2.1 correction controls the
corrected Rev.2 pair; the corrected pair controls the initial draft. The final
Judge controls authority and closure. Later accepted P-OBS-0B publish findings
control the packaging transaction wording without authorizing execution.

## A. Executive and exact host findings

The target is a native x64 OBS adapter that receives audio only from the
Owner-selected OBS source. The adapter preserves exact timing, loss and format
facts and emits bounded receipts. It never decides Dataset adoption or starts
training.

Read-only host Evidence observed OBS Studio `32.2.1` x64. The observed public
binary hashes were:

- `obs64.exe`: `b1541d18fd28a41e78251e885df1440eac619caf7bc00190c8cdcdd45c2bb7f5`;
- `obs.dll`: `fa75071d5493912f3dd4a53ed05c367cd0106fbebd35d0b88abdce9632f8a02f`;
- `obs-frontend-api.dll`: `ff50938708ba68192dc8d4015235b73a4296abb1b160c677769721c0cd080dda`.

These runtime binaries do not prove SDK headers, import libraries, CMake
packages, successful build, Plugin load or capture readiness. The public source
baseline is official tag `32.2.1`, tag object `5997998a...`, commit
`0052d024fd6a5ff1aa04c76cbdffd3085a5dfacc`. The tag is unsigned; identity is
pinned, but cryptographic trust is not claimed. Windows 11 x64 and OBS 32.2.1
are probe baselines, not forward-compatibility claims.

The physical XLR microphone cannot be inferred from an OBS endpoint name. The
exact interface channel, routing and processing chain remain `PROBE_REQUIRED`.
Synthetic success never authorizes Owner-voice or production recording.

## B. Authority and no-duplicate matrix

| Truth | Canonical owner | P-OBS holding | P-OBS prohibition |
|---|---|---|---|
| Voice Profile / Consent | TASK-014 / TASK-046 | opaque exact refs/hashes | second Voice Profile or Consent truth |
| Session / Segment / Attempt / sentence checkpoint | TASK-046 P-VS-3A | issued IDs and semantic receipt refs | ID generation or semantic state decision |
| Capture transport / adapter internal state | TASK-047 P-OBS | commands, adapter events, staging facts | Dataset or quality decision |
| Durable Job / recovery checkpoint | TASK-043 | structured binding | second queue or `PROJECT_MAINTENANCE` reuse |
| Asset / byte revision | TASK-003 | promotion binding/receipt only | in-place Assetization or registry duplication |
| Quality / clipping policy | TASK-048 | facts and opaque quality ref | PASS/FAIL, threshold or clipping decision |
| Resource admission | TASK-020 | opaque receipt | scheduler duplication |
| Dataset adoption / training | TASK-046 + Human Gate | false authority flags | automatic adoption or training |

P-VS-3A names are design references until their implementation is hosted and
bound. P-OBS must not import or claim an absent API. Semantic and durable
checkpoints remain separate records linked only by exact refs/hashes.

## C. OBS version, architecture, ABI and processing-point binding

The future module is x64 native C/C++. `OBS_DECLARE_MODULE`, exported module
version, header/import-library provenance and runtime ABI must be built from
the exact audited source/toolchain contract. A load-version check alone is not
behavioral compatibility proof.

Every production-capable capture requires a
`CallbackAudioProcessingPointBinding` with:

- OBS/libobs tag, commit and relevant blob hashes;
- callback API revision;
- observed format, sample-rate and layout authorities;
- pre/post filter, volume, balance/force-mono, mute, mixer and monitoring state;
- source-code Evidence ref/hash and target synthetic probe ref/hash;
- `result = BOUND_VERIFIED | MISMATCH | UNKNOWN`.

Pinned source Evidence indicates an OBS base-audio/callback boundary and mutex
serialization behavior, but it does not prove exact target-host filter/mixer,
device-native or concurrency behavior. `MISMATCH` and `UNKNOWN` block
production readiness.

## D. Packaging, install, update and rollback boundary

No current operation is authorized. A future package must have exact manifest,
file hashes, module ID, architecture, data/locale layout, provenance, notices
and collision checks. It must never overwrite, auto-rename or side-load around
an existing Plugin.

The publish design is a `JournaledTransactionalPluginPublish` proposal, not an
atomicity claim. A future authorized probe must verify same-volume staging and
target, OBS PID zero, no reparse traversal, containment, journal durability,
the chosen Windows rename/replace semantics and every target-file read-back
hash. States are:

`PENDING_STAGED -> PUBLISHING -> VERIFIED_INSTALLED | FAILED_KNOWN | UNKNOWN | CORRUPT_OR_INCOMPLETE`.

Timeout, crash or partial visibility never auto-succeeds or auto-rolls back.
Rollback is a separate recovery operation with its own identity/idempotency and
`ROLLBACK_VERIFIED` result only after authoritative old-manifest/hash read-back.
It never rewrites prior `UNKNOWN` or `CORRUPT_OR_INCOMPLETE` history. The Owner
will perform a future manual install only after a separate explicit Gate.

## E. Selected-source stable private identity and Public redaction

`SelectedSourceBinding` Private fields include:

- `obs_profile_private_ref`, revision and hash;
- `scene_collection_private_ref`, revision and hash;
- `scene_source_graph_digest`;
- `source_uuid`, type ID, settings digest and filter-chain digest;
- `selected_endpoint_binding` and `observed_at`.

Display names are non-authoritative. Profile/Collection switch, graph
replacement, same-name/different-UUID, restored backup collection, missing UUID
or endpoint drift emits `SOURCE_SCOPE_CHANGED` or `UNKNOWN`, stops capture and
requires fresh preflight. There is no automatic rebind.

Public projections contain only opaque/salted refs, revisions, states and
receipt digests. UUID, device fingerprint, Profile/Collection identity, graph
detail, settings, host path and audio/body hash are prohibited.

## F. P-VS-3A command, event and Evidence mapping

Commands are `START`, `PAUSE`, `RESUME`, `STOP`, `CANCEL`. The envelope binds
contract revision, command/operation/idempotency identity, Project, P-VS-issued
Session/Segment/Attempt IDs, expected semantic revision, adapter revision/hash,
selected-source binding, Consent snapshot digest, cue/text digest, target
format, issued time and command hash.

The adapter generates no Session, Segment or Attempt identity. `RESUME` requires
the same cue/sentence and a new P-VS-issued Attempt identity. `PAUSE` returns
exact drain/range/incomplete-capture Evidence; P-VS decides sentence and
semantic checkpoint state. `CANCEL` returns `CANCEL_ACKNOWLEDGED`, retained
staging-ledger ref/hash and known/unknown external state. P-VS decides exact
`CANCELLED`, `CANCELLED_WITH_RETAINED_EVIDENCE` or `UNKNOWN` state.

Events include `COMMAND_ACCEPTED`, `COMMAND_REJECTED`, `CAPTURE_STARTED`,
`PAUSE_ACKNOWLEDGED`, `RESUME_STARTED`, `STOP_ACKNOWLEDGED`,
`CANCEL_ACKNOWLEDGED`, `CAPTURE_DISCONTINUITY`, `SOURCE_LOST`,
`SOURCE_SCOPE_CHANGED`, `FORMAT_MISMATCH`, `CAPTURE_FAILED_KNOWN`,
`CAPTURE_UNKNOWN` and `ADAPTER_RESTARTED`. Each carries event identity,
sequence, monotonic time, causation, P-VS identities, adapter revision, bounded
facts and receipt ref/hash. Command acknowledgement is never captured success.

## G. Audio callback real-time safety

The callback performs only an overflow-checked, non-blocking copy of a complete
bounded native callback unit plus minimum metadata into preallocated storage.
It performs no disk or network I/O, JSON, formatted logging, blocking lock,
libobs re-entry, callback removal, allocation/growth, resampling, channel
analysis, analyzer/model/RX work or encryption.

`ProducerConcurrencyBinding` records source-code Evidence, observed callback
thread/epoch, maximum simultaneous depth, violation count and target stress
probe hash. SPSC is usable only when `BOUND_VERIFIED`. A concurrent/reentrant
callback increments a fact counter, copies zero frames and fails closed to
`CAPTURE_UNKNOWN`. Detach requires controller removal, bounded in-flight zero
and drain; timeout or late callback does not free state or claim success.

## H. Bounded ring, backpressure and oversized callbacks

The Probe-bound profile fixes expected maximum frames, channels/planes, bytes
per plane, sample width/layout and slot capacity. Checked multiplication and
addition validate every actual bound before copying.

If a pointer/layout is invalid or one plane exceeds capacity, partial copy is
forbidden. Exact known frames are recorded as
`oversized_callback_dropped_frames` and an event count; the range becomes a
`CAPTURE_DISCONTINUITY`, so success is impossible. Unknown pointer/layout stays
`UNKNOWN`. A slot is published with a single release operation only after every
plane copy succeeds. There is no dynamic growth, blocking fallback or partial
plane publication.

Ring-full, overrun, drop and discontinuity counts always carry known flags.
Unknown counts are not written as zero.

## I. Declared/measured format, channel and canonical conversion receipt

Declared and measured input format are distinct. `MonoChannelSelectionBinding`
uses `SELECT_EXACT_CHANNEL` or `VERIFIED_WEIGHTED_DOWNMIX` and records exact
input index/label/private map, Owner physical-chain confirmation, rational
coefficients/config hash and phase/cancellation probe. Input 1/2 are not
averaged by default; Loopback is not remapped to a microphone.

The canonical staging format is signed PCM S24LE, packed three bytes per sample,
little-endian two's complement, mono, 48 kHz. Channel mapping occurs before
resampling. The receipt fixes float valid-range/non-finite handling,
half-away-from-zero deterministic rounding, saturation limits, dither policy,
resampler library/version/license/config/filter/delay/tail/state, cumulative
rational sample mapping, remainder, output count and hash. Until an exact
resampler profile is selected, state is `PROBE_REQUIRED`.

Fact counters are separate:

- `input_non_finite_count`;
- `input_out_of_nominal_range_count` (`x < -1` or `x > 1`);
- `input_full_scale_or_beyond_count` (`x <= -1` or `x >= 1`);
- `quantizer_saturation_count`;
- `packed_output_min_sample_count` and `packed_output_max_sample_count`.

There is no `input_clipping_count`. P-OBS does not issue a clipping quality
decision. TASK-048 owns event/run policy and PASS/FAIL decisions.

## J. Staging, encryption, recovery and TASK-003 handoff

Worker output creates two separate immutable staging lineages:

1. `OBS_CALLBACK_AUDIO_STAGING`;
2. `CANONICAL_48K_S24_MONO_STAGING`.

Every staging revision fixes
`asset_registration_authorized=false`,
`dataset_adoption_permitted=false`,
`training_use_permitted=false` and
`public_exposure=false`.

`STOP` success reaches only `CAPTURE_STAGING_FINALIZED`. CANCEL retained
Evidence remains in the staging ledger. TASK-003 Asset registration/promotion
is a separate Owner decision and external effect with its own operation
identity, idempotency and canonical receipt. Staging is never mutated in place
into an Asset, and no Asset success is displayed without that receipt.

Encryption, key custody, ACL, retention and crash-recovery mechanisms are
separate hosted prerequisites. This design persists no key value or real path.

## K. TASK-043 durable Job and restart binding

`CaptureDurableJobBinding` records canonical ref/version/hash, capture kind,
dispatch/status/cancel/reconcile APIs, CAS/idempotency/checkpoint/event/UNKNOWN
rules and Evidence hash. States are
`CANONICAL_REF_NOT_PROVIDED | BOUND_VERIFIED | MISMATCH | UNKNOWN`.

Current hosted TASK-043 has no voice-capture kind. Its generic recovery
primitives do not authorize capture capability. `PROJECT_MAINTENANCE` reuse and
a second P-OBS queue are forbidden. Until the binding is `BOUND_VERIFIED`,
durable production dispatch is blocked.

## L. TASK-048 gain, noise, clip and calibration boundary

P-OBS records measurements and exact facts. TASK-048 owns calibration profile,
quality policy, clipping/run judgment, noise/level thresholds and any rerecord
recommendation. Missing or unhosted P-QC bindings remain opaque optional refs
with `CANONICAL_REF_NOT_PROVIDED`; they never default PASS. Owner hardware gain,
48 V, PAD, HPF and routing are Human Gates.

## M. Pause/resume sentence and checkpoint behavior

PAUSE performs a bounded drain and returns source/canonical ranges and
incomplete-capture facts. P-VS records the semantic checkpoint. A partial
sentence Attempt remains immutable. RESUME starts the same cue/sentence from
its beginning using the new P-VS-issued Attempt. Partial-sentence splice is
forbidden. Environment or day/session changes require fresh source, format,
Consent, resource, encryption and recovery preflight; there is no auto resume.

## N. Crash, source change, device loss and OBS restart

Source removal, graph/scope change, filter/volume/mute/mixer drift, format
change, device loss, Plugin crash, OBS restart, callback concurrency violation,
oversized input or ambiguous stop emits exact facts and a known-failure or
UNKNOWN event. Capture stops and requires reconciliation and fresh preflight.
UNKNOWN is never automatically replayed, cancelled or accepted.

## O. Privacy, security and threat model

Threats include malicious DLL/search path, package/manifest tamper,
symlink/reparse traversal, source-swap TOCTOU, stale/replayed command, IPC
spoofing, public-log leakage, staging theft, callback starvation and crash
truncation. Future controls require exact package provenance, containment,
authenticated local IPC, CAS/idempotency, source identity before/after attach,
bounded memory, encrypted staging, append-only manifests and redacted Public
projection. These controls are requirements, not implementation claims.

## P. RX 12 offline post-capture boundary

RX never runs in the real-time callback or live worker. Only after a separate
TASK-003 Assetization Gate may an offline authorized Job create a new derived
revision candidate with exact tool/version/preset/input/output hashes. Original
recording and staging are never overwritten.

## Q. Synthetic and target-host probe plan

Static probes cover exact headers/ABI/export/PE x64, callback forbidden-call
lint and call graph. Synthetic probes cover commands, events, ranges, ring
overflow, callback concurrency, all-plane publication, golden S24 bytes,
NaN/Inf, rounding, saturation, resampler delay/tail/remainder and public
redaction. Target-host probes independently vary filter, volume, balance,
force-mono, mute, mixer, monitoring, Profile, Scene Collection, graph, source,
format and device state and hash the observed callback bytes/flags/ranges.

Source-code Evidence, synthetic Evidence and target-host Evidence have separate
refs/hashes. None alone authorizes production recording.

## R. Future Lock, Allowed Files and build prerequisites

The next possible Product slice is a pure metadata transport contract only
after this design and P-VS-3A implementation are hosted and a separate exact
Lock/authorization exists. TASK-043, TASK-003 and P-QC may remain structured
unresolved bindings only when all dispatch/effect flags remain false.

Native work additionally requires exact acquired source/template provenance,
headers/import libraries, generated headers, toolchain, no-network configure,
dependency-cache hashes, license/source-offer review, packaging/signing/trust
decisions and independent configure/build/package/load Gates. Installed DLLs
or tool executables are not substitutes. The T0 Microsoft catalog mismatch
remains blocked. No current download, install, build, load or capture is
authorized.

## S. Acceptance matrix

The following must fail closed or produce the exact bounded result:

1. normal START/PAUSE/RESUME/STOP;
2. CANCEL with retained staging Evidence;
3. wrong/stale Session, Segment, Attempt or command revision;
4. duplicate command returns same receipt; differing payload conflicts;
5. duplicate/out-of-order event quarantine;
6. wrong source, source switch or same-name different UUID;
7. Profile/Scene Collection/graph switch or restored backup collection;
8. missing UUID or endpoint binding;
9. declared/measured format mismatch;
10. device disconnect, Plugin crash or OBS restart;
11. ring overflow and exact known drop facts;
12. unknown loss/count is not zero;
13. callback processing binding UNKNOWN/MISMATCH blocks production;
14. filter/volume/balance/mute/mixer change is not ignored;
15. muted range is quarantined and not auto-adopted;
16. wrong/empty channel, half-gain average and Loopback selection rejected;
17. phase-cancelling downmix rejected;
18. unidentified XLR chain remains `PROBE_REQUIRED`;
19. reentrant/concurrent callback copies zero;
20. detach timeout does not free or succeed;
21. oversized frames/channels/plane bytes drop the whole unit;
22. null pointer, arithmetic overflow and partial plane publish rejected;
23. `x=-1`, `x=+1`, out-of-range and long full-scale runs remain separate facts;
24. NaN/Inf is not silently coerced;
25. packed3/endian/container ambiguity rejected;
26. resampler delay/tail/remainder/sample-map tamper rejected;
27. command ACK alone cannot claim captured success;
28. auto Assetization and staging-to-Asset in-place mutation rejected;
29. Asset success without TASK-003 receipt rejected;
30. Adapter-generated semantic IDs/states rejected;
31. partial-sentence splice rejected;
32. absent TASK-043 binding or `PROJECT_MAINTENANCE` reuse blocks dispatch;
33. second Job/Queue creation rejected;
34. RX destructive overwrite rejected;
35. public audio/body/path/device/Profile/Collection/graph leakage rejected;
36. ABI mismatch and Plugin collision blocked;
37. unsigned identity is not trust PASS;
38. unproven package atomicity/rollback success rejected;
39. synthetic/build/load success cannot promote production;
40. Owner Consent, encryption/storage and Owner GO remain separate Gates.

## T. Critic reviews and corrections

Critic pass 1 found three High and three Medium issues: staging-to-Asset leap,
P-VS semantic duplication, unbound processing/mute/channel policy, unhosted
TASK-043 capability, unproven SPSC and ambiguous S24 conversion. Rev.2 replaced
these with two staging lineages, explicit owner boundaries, structured
bindings, conditional concurrency and byte-exact conversion.

Critic pass 2 found three Medium issues: full-scale facts mislabeled clipping,
source identity missing Profile/Scene Collection/graph scope and oversized
callbacks permitting partial publication. Rev.2.1 separated fact/decision
layers, expanded scope identity and required whole-unit drop plus single-release
publication. A later publish Critic replaced unproven atomicity with the
journaled transaction and separate recovery operation.

Obsolete clauses are rejected: `input_clipping_count`, device-raw wording,
auto Asset/Dataset/training, Adapter-created semantic IDs/state, unconditional
SPSC, partial copy/publish, unknown-as-zero, implicit downmix, real-time RX and
synthetic-to-production promotion.

Post-correction unresolved Critical / High / Medium: `0 / 0 / 0`.

## U. Read-only Judge

`PASS_FOR_READ_ONLY_DESIGN_CLOSURE`

`IMPLEMENTATION_NOT_AUTHORIZED`

`PLUGIN_BUILD_INSTALL_LOAD_NOT_AUTHORIZED`

`OBS_LAUNCH_CONFIG_CAPTURE_NOT_AUTHORIZED`

`AUDIO_DEVICE_ASSET_DATASET_MUTATION_NOT_AUTHORIZED`

Residual Critical / High / Medium: `0 / 0 / 0`.

P-OBS-1A read-only design is complete. Completion of this document does not
authorize Plugin implementation, host changes or production recording.
