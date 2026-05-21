# Scheduling Infrastructure (Generic Subdomain)

> Classification: **Generic**

**Business Purpose:**
Trigger periodic executions (07:00 briefing, 22:00 reflect, weekly/monthly/yearly consolidations, periodic fetch) through the OS-native job scheduler, outside the AI assistant. The AI is the skill execution engine, not the scheduler.

**Key Capabilities:**

- launchd plists generated at bootstrap (macOS primary, PRD §8)
- cron / systemd user timers as Linux fallback
- Claude Code hooks SessionStart (optional `next`) / PreCompact (snapshot) / SessionEnd (`reflect day`)
- Cadence overrides via `anatomy/preferences.md > ## Cadences` (user-managed)
- Optional lightweight cron for `next` (user choice at bootstrap)

**Strategic Importance:**
Pure commodity. OS-level scheduling is a well-understood facility. The strategic decision (D-37 §3.3) is to schedule **outside** the AI assistant so the runtime choice stays free; the implementation itself is standard. Differentiator is *negative* (NOT depending on the AI), not in the implementation.

**Complexity Assessment:**
Low — declarative plist/cron generation at bootstrap + reading preferences for overrides. Tested on macOS/Linux. Windows out of scope for v1.

**Data Ownership:**
Plist files under `~/Library/LaunchAgents/com.gilberto.*` (macOS), cron entries / systemd units (Linux). Generated and managed by `gilberto-process-vault-bootstrap` + `gilberto-process-vault-upgrade`. `anatomy/preferences.md > ## Cadences` is the authoritative source.

**Dependencies:**

- Depends on: Vault Lifecycle (bootstrap generates plists), Adaptive Anatomy (preferences for cadences)
- Provides to: Cognitive Operations (temporal triggers for surface 07:00, reflect 22:00, periodic fetch)

**Team Recommendations:**
Single-contributor in v1. Profile: system-admin (launchd/cron/systemd). Linux supported (PRD §8 Constraints). Windows out of scope.

**Implementation Priority:**
Low — Phase 1 base setup (M1 bootstrap generates plists), Phase 2 active cadences (M3 morning-briefing + reflect-day end-to-end). Linux porting Medium-priority post-v1.
