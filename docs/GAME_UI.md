# Penny's game-style public interface
Status: interaction and design contract; no final artwork or live deployment.
Penny is the main character, not a dashboard mascot. Simple readable
mobile-first UI with a game dialogue scene, persistent progress and credit.
Slogan: Financially Underfunded. Sarcastically Overqualified.

## Home screen hierarchy
1. Header: name, slogan, actual availability (available, busy, full, paused,
   offline or stale), chapter. Never claim online without a fresh heartbeat.
2. Main scene: canonical Penny character in current milestone-based room,
   controlled expressions (idle, thinking, talking, celebrating); local
   browser animation, no inference needed to render. Final assets/voice
   require approval. Respect reduced-motion settings.
3. Large readable dialogue bubble: latest private answer for signed-in
   member, public welcome/approved diary excerpt otherwise. Clear AI/fiction
   disclosure. Long answers scroll/expand; never truncate meaning.
4. Question input (max 2000 chars), Send, character count, sign-in when
   required. Accessible keyboard and screen-reader feedback. Preserve draft
   on busy/error; no fake typing or progress. One outstanding free task
   under existing scheduler policy. Show queued/working/answered/error states.
   Keep private replies out of shared HTML, caches and public activity feeds.
5. Mission progress: verified financial metric or unavailable, next objective,
   actual update timestamp. Never display fabricated earnings or percentage.
6. Achievement Center: compact unlocked/locked milestone tiles, title, date,
   evidence-backed explanation, next milestone. Examples: first verified
   dollar, first profitable venture, first owned compute upgrade. Development
   milestones distinct from financial achievements. No award based on fiction.
7. Greatest Contributors: visible opt-in public aliases, verified roles and
   outcome summaries, equal credit regardless of paid tier. Initial showcase
   grouped by verified impact/outcome; ranking formula not approved. No fake
   names, monetary rankings, or public identity without consent. Ties fairly
   represented. Corrections/revocations remove current attribution.
8. Compact bottom navigation: Home, Progress, Vault, Council, Diary.
   Additional ventures, wishlist, settings and personal history accessible
   within sections without cluttering home. No dead buttons in released UI.

## Interaction and state
Home uses cached public snapshot; chat uses owner-bound private API. Anonymous
visitors can browse without LLM calls. Signed-in member submits text and sees
the acknowledged state, then polls only while outstanding and tab visible;
backoff on delays/errors. Do not let multiple tabs duplicate messages.
Render model responses as escaped text; no arbitrary HTML or script.
Conversation history accessible from home but not the default visual focus.
Penny can publish approved expressions and commentary via typed snapshot
fields; she cannot edit site code, alter identity artwork, or directly write
public facts. Character pose conveys system state, not evidence of feelings.

## Definition of done
Responsive layout, readable contrast and font scaling, accessible controls,
no layout shift on long replies, reduced-motion support. Offline state shows
last verified world without false live status. Public contributor display
respects explicit consent and withdrawal. Achievements unlock only from
verified local records. Synthetic preview data labeled and excluded from
production. Backend, API, authentication, cost and security acceptance in
NETLIFY_BRIDGE.md must pass before public interactive launch.
