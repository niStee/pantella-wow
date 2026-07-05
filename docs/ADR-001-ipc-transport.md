# ADR-001: Addon-to-Backend IPC Transport

## Status

**Milestones 1–2 implemented.** This slice (2026-07-05) delivers:
1. Normalized message-envelope definition and Python-side transport interface (`game_interfaces/transport/combat_log.py`).
2. Combat-log proof: `C_ChatInfo.SendAddonMessageLogged` emits bounded JSON event messages from `MantellaWoW.lua`; the Python backend tails `WoWCombatLog.txt` via `watchdog` and parses through the envelope.

Chunking and sequence reassembly (255-byte payload limit management) are **deferred to a future slice**.

## Revision History

| Date | Change |
|---|---|
| 2026-07-03 | Initial version: pixel encoding as primary, combat log as secondary. |
| 2026-07-04 | Revised transport priority after prior art review. Combat log promoted to primary; pixel encoding demoted to optional high-frequency supplement. Envelope clarifications added (timestamp ownership, sequence ownership, checksum requirements). |
| 2026-07-05 | Slice 1 implementation: Milestones 1-2 delivered. Chunking/reassembly marked deferred. Status updated from "Accepted" to "Milestones 1-2 implemented". |

## Context

Pantella-WoW needs to move live game state from the WoW Lua addon to the Python backend without violating WoW's sandbox or relying on APIs that do not exist in the retail client.

The previous prototype attempted to write JSON into a Lua `EditBox` and read it from Python with Win32 `WM_GETTEXT`. Testing on WoW 12.0.7 showed this cannot work as a live bridge: the WoW process window is discoverable as `waApplication Window`, but Lua UI frames are rendered internally and are not Win32 child controls. `EnumChildWindows` does not expose the addon-created `EditBox`, so `WM_GETTEXT` is retired as an IPC mechanism rather than temporarily broken.

WoW Lua also cannot safely provide the missing bridge through HTTP, sockets, named pipes, clipboard access, direct file I/O, or memory reading. Those are either unavailable in the sandbox or unacceptable for a ToS-conscious addon/backend design.

### Prior Art

The combat log tail approach is the most battle-tested WoW→external IPC pattern in the community. Warcraft Logs, ACT (Advanced Combat Tracker), Twitch's overlay integration, and numerous raid-logging tools all rely on tailing `WoWCombatLog.txt` combined with `C_ChatInfo.SendAddonMessageLogged`. This is proven at scale, has zero Win32 dependency, and works in all window modes (windowed, fullscreen, minimised).

Pixel encoding has prior art in [`wodim/wow-discord-rich-presence`](https://github.com/wodim/wow-discord-rich-presence), which uses coloured pixel squares in a Lua frame captured by Python/Pillow. That project validates the concept for low-frequency, simple state (Discord presence), but requires manual per-system calibration and is fragile to overlays, HDR pipelines, UI scale, and fullscreen exclusive mode. It has not been demonstrated for high-frequency live game state.

## Decision

Pantella-WoW will use a channel-neutral IPC abstraction. Backend logic consumes normalized messages from transports; it must not depend on one transport's wire format.

The target transport stack is, in priority order:

1. **Combat log addon messages as the primary live-state channel.** `C_ChatInfo.SendAddonMessageLogged` carries structured event messages that the backend reads by tailing `WoWCombatLog.txt`. The 255-byte per-message payload limit is handled by chunking and sequence reassembly. Latency is 100–300 ms with a tight Python `watchdog` or polling loop. This is the transport that must work first and must be kept working.
2. **SavedVariables as a bulk state and recovery channel.** SavedVariables may carry large state snapshots, configuration, and crash/reload recovery data. They are flushed on logout or `/reload`; they are not a live gameplay transport and must not be treated as one.
3. **Pixel encoding as an optional high-frequency supplement.** If combat log throughput (255 bytes/msg, Blizzard-throttled) proves insufficient for high-frequency live NPC state deltas, a pixel strip transport may be added. The addon renders a small pixel strip; the backend captures the WoW window via Windows Graphics Capture or DXGI and decodes the pixels. This transport is gated on combat log proving insufficient — it must not be built speculatively. The pixel capture component is being developed in `overlay.py`.

## Message Envelope

Every transport must emit the same logical envelope after decoding:

```json
{
  "version": 1,
  "channel": "combat_log|saved_variables|pixel",
  "sequence": 123,
  "timestamp_ms": 1780000000000,
  "type": "state_delta|event|snapshot|health",
  "payload": {},
  "checksum": "required for pixel; optional for combat_log and saved_variables"
}
```

Transport-specific framing may differ, but normalized backend events must preserve these fields or an explicitly versioned successor.

**Timestamp ownership:** `timestamp_ms` is Unix epoch milliseconds (UTC) assigned by the Python backend at ingest time. The Lua addon side supplies a `sequence` number only; it has no reliable clock source for cross-transport ordering.

**Sequence ownership:**
- For combat log: sequence is assigned by the Python parser at ingest time, incrementing per parsed line.
- For pixel transport: sequence is addon-assigned and encoded in the pixel frame header.
- For SavedVariables: sequence is not meaningful; use `type: snapshot` with a full state payload.

**Checksum:** Required for pixel transport due to capture fragility (color drift, HDR, overlays). Optional for combat log (Blizzard guarantees log line integrity) and SavedVariables (filesystem guarantees).

## Consequences

- Combat log transport has payload limits (255 bytes/msg), Blizzard-side throttling, channel requirements (`LOGGED` channel must be enabled), and gameplay-context restrictions. These are well-understood and managed by chunking and the sequence reassembly layer.
- Pixel capture remains available as a supplement but carries significant validation cost: it must be tested across UI scale, resolution changes, windowed/fullscreen modes, HDR/color filters, overlays, occlusion, and minimised-window behaviour before it can be considered reliable.
- SavedVariables are useful for durability and bulk transfer but logout/reload flush semantics disqualify them from real-time IPC.
- The abstraction prevents a proof-of-concept transport from leaking into business logic. The backend should parse normalized messages, not care whether they arrived through log lines, pixels, or recovery files.

## Anti-Goals

- Do not revive Win32 child-control scraping for WoW Lua UI frames.
- Do not read WoW process memory.
- Do not require sockets, named pipes, HTTP, clipboard access, or direct file writes from Lua.
- Do not describe SavedVariables polling as live gameplay IPC.
- Do not build pixel encoding speculatively before combat log transport is proven insufficient.
- Do not make core Pantella changes when the WoW addon/backend adapter can contain the transport abstraction.

## Implementation Milestones

1. ✅ Define the normalized message envelope and Python-side transport interface (channel-neutral). **Delivered 2026-07-05.**
2. ✅ Build a combat-log proof: emit a small bounded event message via `SendAddonMessageLogged`, tail `WoWCombatLog.txt` in Python, parse through the envelope. This is the transport that must be production-ready. **Delivered 2026-07-05.**
3. ⬜ Build SavedVariables bulk channel: write full state snapshot on `/reload`, read from Python on file change.
4. ⬜ Add channel health reporting so the backend can expose which transports are active, degraded, or unavailable.
5. ⬜ Keep SavedVariables limited to configuration handoff, last-known state, and reload recovery.
6. *(Conditional on milestone 2 proving insufficient)* Build a pixel-encoding prototype with sequence, length, version, and mandatory checksum framing. Validate across: 1080p and 4K, windowed and fullscreen, UI scale 0.64–1.0, one active overlay (e.g. Discord), and minimised-window behaviour. All axes must pass before pixel transport is promoted to active use. Pixel capture component lives in `overlay.py`.

> **Chunking and sequence reassembly** (needed to handle the 255-byte per-message limit of `SendAddonMessageLogged`) are **deferred** to a future slice. Current implementation emits single-message payloads only; multi-message payloads are silently dropped if they exceed the byte limit. This will be addressed when throughput requirements are characterized.
