# ADR-001: Addon-to-Backend IPC Transport

## Status

Accepted for the next implementation pass.

## Context

Pantella-WoW needs to move live game state from the WoW Lua addon to the Python backend without violating WoW's sandbox or relying on APIs that do not exist in the retail client.

The previous prototype attempted to write JSON into a Lua `EditBox` and read it from Python with Win32 `WM_GETTEXT`. Testing on WoW 12.0.7 showed this cannot work as a live bridge: the WoW process window is discoverable as `waApplication Window`, but Lua UI frames are rendered internally and are not Win32 child controls. `EnumChildWindows` does not expose the addon-created `EditBox`, so `WM_GETTEXT` is retired as an IPC mechanism rather than temporarily broken.

WoW Lua also cannot safely provide the missing bridge through HTTP, sockets, named pipes, clipboard access, direct file I/O, or memory reading. Those are either unavailable in the sandbox or unacceptable for a ToS-conscious addon/backend design.

## Decision

Pantella-WoW will use a channel-neutral IPC abstraction. Backend logic consumes normalized messages from transports; it must not depend on one transport's wire format.

The target transport stack is:

1. **Pixel encoding as the primary live-state channel.** The addon renders a small pixel strip containing framed state data. The backend captures the WoW window via Windows Graphics Capture or DXGI and decodes the pixels.
2. **Combat log addon messages as a secondary event/fallback channel.** `C_ChatInfo.SendAddonMessageLogged` may carry small event messages that the backend reads from `WoWCombatLog.txt`.
3. **SavedVariables as persistence and recovery only.** SavedVariables may store configuration, last-known state, or crash/reload recovery data, but are not a live gameplay transport.

A narrow combat-log proof may be implemented first to validate message envelopes, parser behavior, and backend integration. That proof does not promote combat log to the primary architecture.

## Message Envelope

Every transport must emit the same logical envelope after decoding:

```json
{
  "version": 1,
  "channel": "pixel|combat_log|saved_variables",
  "sequence": 123,
  "timestamp_ms": 1780000000000,
  "type": "state_delta|event|snapshot|health",
  "payload": {},
  "checksum": "optional-integrity-marker"
}
```

Transport-specific framing may differ, but normalized backend events must preserve these fields or an explicitly versioned successor.

## Consequences

- Pixel capture is the main technical risk. It must be validated across UI scale, resolution changes, windowed/fullscreen modes, HDR/color filters, overlays, occlusion, and minimized-window behavior.
- Combat log transport is useful because it is simple and observable, but it is not authoritative. It has payload limits, throttling, channel requirements, and gameplay-context restrictions.
- SavedVariables are useful for durability, but logout/reload flush semantics disqualify them from real-time IPC.
- The abstraction prevents a proof-of-concept transport from leaking into business logic. The backend should parse normalized messages, not care whether they arrived through pixels, log lines, or recovery files.

## Anti-Goals

- Do not revive Win32 child-control scraping for WoW Lua UI frames.
- Do not read WoW process memory.
- Do not require sockets, named pipes, HTTP, clipboard access, or direct file writes from Lua.
- Do not describe SavedVariables polling as live gameplay IPC.
- Do not make core Pantella changes when the WoW addon/backend adapter can contain the transport abstraction.

## Implementation Milestones

1. Define the normalized message envelope and Python-side transport interface.
2. Build a combat-log proof that emits and parses a tiny bounded event message through the envelope.
3. Build a pixel-encoding prototype with sequence, length, version, and checksum framing.
4. Add channel health reporting so the backend can expose which transports are active, degraded, or unavailable.
5. Keep SavedVariables limited to configuration handoff, last-known state, and reload recovery.
