# TASK-028 — AI Connection Provider / Model Routing

- Status: `ROUTING CORE IMPLEMENTED / NATIVE WINDOWS REGRESSION PENDING`
- Package: `0.6.0`
- Governance: `DEV-4 EXTERNAL PROVIDER AND COST CONTROL`
- Authorization: Owner-requested implementation

## Objective

企画、動画、画像、音声、音楽ごとに、上位方針と具体的なProvider/Modelを変更可能にする。設定された経路以外を暗黙に利用せず、利用不能時は安全にフォールバックまたは失敗する。

## Implemented scope

- Workload: `PLANNING / VIDEO / IMAGE / AUDIO / MUSIC`
- Mode: `AI / FREE / AUTO / OFFLINE_ONLY / DISABLED`
- Provider family: OpenAI, Anthropic (Claude), Google (Gemini), ComfyUI, Audacity/OpenVINO, local open source, non-AI library, other
- exact `provider_id`, `model_id`, planning `reasoning_effort`, priority and required capability
- paid/free/local classification and availability/credential filtering
- secret-free `credential://` and `endpoint://` references
- canonical JSON, SHA-256 integrity check, schema and packaged example

`gpt-5-sol` and `medium` are accepted as configured identifiers in the example. This is not a claim that a named provider currently exposes that exact model; deployers must choose identifiers supported by their installed adapter/account.

## Boundary

This slice implements the configuration and resolver contract. Provider-specific HTTP clients, credential-store integrations and the GUI settings panel are subsequent adapter/UI slices. Those components must execute only the route returned by this resolver.

## Acceptance

The resolver must honor workload mode, cost/locality, availability, credentials, capability and priority; reject embedded secrets; load checksum-valid persisted profiles; fail closed when no eligible route exists; and keep all schemas packaged.
