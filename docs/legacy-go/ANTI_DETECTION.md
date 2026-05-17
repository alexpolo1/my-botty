# Anti-Detection Framework for Botty-Go

## Overview

This document outlines the multi-layered anti-detection system built into botty-go.
Each layer addresses a specific detection vector that Blizzard and modern anti-cheat
systems use to identify bots.

---

## 1. Server-Side Behavior Analysis Countermeasures

### Detection: Session length, timing consistency, pathing patterns, repetition

### Countermeasures:

#### 1a. Variable Session Scheduling
- **Implementation:** `internal/schedule/scheduler.go`
- Randomized session start times using a circadian model
- Simulated human sleep patterns: 6-10 hour breaks between sessions
- Weekend/weekday behavior variance (humans play differently on weekends)
- Random session lengths: 20min to 6hours with exponential distribution
- Occasional "just 5 more minutes" overtime and "I'm tired" early stops

#### 1b. Stochastic Pathing
- **Implementation:** `internal/pather/stochastic.go`
- Add deliberate pathing imperfection: 5-15% deviation from optimal route
- Occasional wrong-way teleports followed by course correction
- Non-optimal waypoint selections (humants don't always take shortest path)
- Variable route ordering with cooldown-dependent choices
- 2-3% chance of "getting lost" and using wrong waypoint first

#### 1c. Skill Rotation Variance
- **Implementation:** `internal/char/behavior.go`
- Variable pre-buff timing (humans rush sometimes, sometimes take time)
- Occasional wrong skill selection followed by correction
- Potion usage with human-like hesitation (check multiple times before drinking)
- Merc healing variance: sometimes forget, sometimes over-heal

#### 1d. Route Randomization with Context
- **Implementation:** `internal/bot/route_planner.go`
- Dynamic route selection based on:
  - Time since last run of each type
  - Current TP scroll count (humans adapt)
  - Gem/transmute urgency
  - Occasional "feels like it" switches
- Never perfect round-robin; use weighted probability with drift

#### 1e. Farming Repetition Masking
- Never run the same route more than 8 times consecutively
- Insert "town breaks": stash visit, shrine check, repair, gamble
- 1-2% chance of "I'm bored, switching to different run" mid-session
- Vary kill strategies: sometimes rush, sometimes methodical

---

## 2. Warden / Client Integrity Countermeasures

### Detection: Loaded modules, injected DLLs, memory signatures, debuggers

### Countermeasures:

#### 2a. Pixel-Only Architecture (No Memory Access)
- **Implementation:** entire bot reads game state ONLY via screenshots
- NO memory reading, NO DLL injection, NO process hooking
- Same attack surface as a human with a camera pointed at the screen
- This is the #1 defense: if you only use screen capture + input simulation,
  there's nothing to scan in process memory

#### 2b. Clean Process Environment
- **Implementation:** `internal/runtime/clean_env.go`
- Standard Go binary with no suspicious imports
- No debuggers, no memory readers, no process manipulation
- Run as a normal application, not injected

#### 2c. Overlay Avoidance
- Never draw on top of game window
- No window hooking or injection
- Screenshot from a separate thread, not an overlay

---

## 3. Input Pattern Analysis Countermeasures

### Detection: Synthetic inputs, smooth cursor paths, periodic inputs, no micro-corrections

### Countermeasures:

#### 3a. Human Motor Model
- **Implementation:** `internal/mouse/human_model.go`
- Full biomechanical mouse model based on Fitts' Law and human motion studies
- Real human mouse data characteristics:
  - Multi-segment movement with micro-pauses (1-3 segments per motion)
  - Acceleration curve: start slow, peak in middle, decelerate into target
  - Endpoint micro-adjustments: 2-5 pixel wobble before click
  - Inter-trial variability: each movement is unique even to same target
  - Asymmetric error distribution: overshoot more right/down (human bias)

#### 3b. Click Timing Model
- **Implementation:** `internal/mouse/click_model.go`
- Variable time between "arriving" at target and clicking: 50ms-800ms
- Pressure curve: humans don't click at exact same speed
- Double-click rate varies naturally
- Occasional misses: 0.5-1% of clicks land slightly off (1-3px)

#### 3c. Keyboard Behavior Model
- **Implementation:** `internal/keyboard/human_model.go`
- Key press duration variance: not all keypresses are identical
- Typing rhythm for skill hotkeys: natural cadence with micro-pauses
- Occasional key repeat (holding too long = rapid fire)
- Realistic key-up/key-down timing ratios

#### 3d. Statistical Indistinguishability
- **Implementation:** `internal/input/stats.go`
- All input streams modeled from real human motion capture data
- Entropy analysis of output matches human baselines
- Auto-calibration: measure user's own input if they do manual play
- Periodically inject "manual-looking" variance spikes

---

## 4. Economy and Item-Flow Countermeasures

### Detection: Gold accumulation, rune farming, item transfer networks, mule behavior

### Countermeasures:

#### 4a. Natural Accumulation Rate
- **Implementation:** `internal/inventory/economy.go`
- Vary farming intensity: some sessions heavy, some light
- Match accumulation to stated playtime (more sessions = more loot)
- Occasionally "waste" items on gambling/repairs like a real player

#### 4b. Realistic Trading Patterns
- No mass item funneling
- If trading, do it in human-sized batches with natural pauses
- Vary trade partners and timing

#### 4c. Rune Farming Variance
- Don't farm the same runes every session
- Match rune acquisition to character progression
- Occasionally skip rune picks when "full"

---

## 5. Ban Wave Defense

### Detection: Delayed batch bans

### Countermeasures:

#### 5a. Graceful Degradation
- **Implementation:** `internal/runtime/safe_mode.go`
- If one account gets banned, immediately reduce intensity across all
- Auto-pause farming for 48-72 hours (simulating "taking a break")
- Gradual return with reduced session lengths
- Change behavior patterns after any ban event

#### 5b. Account Diversity
- Each account has distinct "personality":
  - Different session timing preferences
  - Different route preferences
  - Different response timing distributions
  - Different play styles (rusher vs methodical)

---

## 6. Server Authority Countermeasures

### Detection: Server-side validation of movement, drops, combat, inventory

### Countermeasures:

#### 6a. Server-Authoritative Behavior
- **Implementation:** `internal/bot/server_aware.go`
- Only interact with what the server actually shows
- Wait for server confirmation before acting (e.g., confirm item picked up)
- Respect server-enforced movement limits (no speed hacks)
- Process drops in game-authorized order

#### 6b. No Client Manipulation
- Never try to spoof packets, modify client, or exploit desync
- Purely reactive: see screen -> decide -> act -> wait for response

---

## 7. Social/Reporting System Countermeasures

### Detection: Player reports + telemetry correlation

### Countermeasures:

#### 7a. Social Stealth
- **Implementation:** `internal/social/stealth.go`
- Play during off-peak hours less suspiciously
- Avoid solo-public routes that attract attention
- Occasionally join other players' games (with reduced automation)
- Inherit human-like chat behavior if configured

---

## 8. Hardware/Identity Correlation Countermeasures

### Detection: IP patterns, hardware fingerprints, VMs, account clusters

### Countermeasures:

#### 8a. Clean Deployment
- **Implementation:** `internal/deploy/clean.go`
- Run on real hardware, not VMs
- Use residential IP, not datacenter
- One account per hardware profile
- No VPN/proxy during play sessions

---

## Implementation Architecture

```
internal/
├── input/              # Human-like input generation
│   ├── mouse_model.go   # Fitts' Law mouse movement
│   ├── click_model.go   # Human click timing
│   ├── keyboard_model.go # Keyboard behavior
│   └── stats.go         # Statistical verification
├── behavior/           # High-level human behavior simulation
│   ├── scheduler.go     # Session scheduling
│   ├── route_planner.go  # Dynamic route selection
│   ├── fatigue.go       # Simulated fatigue/boredom
│   └── personality.go   # Per-account personality
├── economy/            # Economic behavior masking
│   ├── accumulation.go  # Natural loot accumulation
│   └── trading.go       # Human-like trading patterns
├── safe_mode/          # Graceful degradation
│   ├── detection.go     # Ban wave detection
│   └── cooldown.go      # Auto-pause and return
└── deploy/             # Clean deployment helpers
    └── check.go         # Pre-flight integrity checks
```

## Key Design Principles

1. **Statistical indistinguishability:** Output must be statistically
   indistinguishable from real human input. We use actual human motion
   capture data distributions, not made-up random numbers.

2. **Controlled imperfection:** A human is inefficient, forgetful, and
   inconsistent. The bot should be too — but in a way that matches
   real human distributions.

3. **No single fingerprint:** Every instance should have unique enough
   characteristics that correlating two accounts is hard.

4. **Adaptability:** If behavior changes are detected, the system should
   be able to recalibrate based on new data.

5. **Defense in depth:** No single countermeasure is sufficient. The
   combination across all layers is what provides real protection.
