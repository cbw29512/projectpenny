# Private inference worker — MVP slice
## Objective
Execute one durable claim using a replaceable local brain. No tool execution, external actions, public API, memory retrieval or payments in this slice.
## State
Claim: existing task UUID, fence UUID, payload, lease_until (UTC epoch seconds). WorkerResult: idle, completed, blocked. BrainConfig: fixed qwen3:14b, localhost:11434, 8192 context, 512 generated tokens, non-thinking mode, one request, no retries. Initial wall-time limit 90s, reserve 5s before claim expiry.
Identity: immutable source-controlled system prompt; user payload is separate and never substituted for identity. Model output is untrusted draft text. This is not a full Guardian or personality certification.
## Flow
Claim transactionally. If no work return idle without inference. Calculate budget from lease and local clock; require synchronized clock. Call local inference via a child process with hard parent timeout. Child HTTP connection is loopback-only and bypasses proxies/redirects; response capped. Accept only finished assistant text, no tools, no truncated response. On success write fenced outcome before releasing claim. Any uncertain inference or storage failure returns blocked, does not retry or release claim. An operator must verify the old Ollama request is stopped before recovery. Killing a client does not prove server inference stopped.
## Acceptance
Fake brain and storage tests: idle no call, one claim per invocation, success fences, malformed output, timeout, lost fence, database errors, no retry. Transport tests: fixed endpoint, role separation, bounded response, reject tool requests. Actual GPU benchmark and end-to-end local test still required. No unattended polling/service deployment until Guardian, recovery and runtime monitoring are ready.
