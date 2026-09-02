# Family Hub — Public Edition Implementation Phases

**Status:** Planned  
**Target:** Friends-and-family beta / public GitHub repository  
**Product model:** Self-hosted household appliance, not a hosted service  
**Primary host:** Windows 10/11  
**Secondary host:** Linux / Raspberry Pi  
**Primary clients:** Large-screen desktop, touchscreen, tablet  
**Phone support:** Best-effort only; not a design target

---

## 1. Purpose

This document defines the work required to turn the existing private Family Hub application into a separate, household-agnostic **public edition** that can be installed and used by friends without requiring them to understand Python, Git, YAML, `.env` files, or the private owner's homelab.

The public edition is **not** a commercial product, SaaS service, or general family-management platform. It is a hobby project shared as-is.

The intended experience is:

1. Download Family Hub.
2. Install it on a Windows PC, or deploy it on Linux / Raspberry Pi using documented instructions.
3. Follow a first-run setup wizard.
4. Connect Google Calendar or configure ICS.
5. Choose optional features such as weather, sports, music, commute, and the public app launcher.
6. Use Family Hub locally on the host device or from a tablet/touchscreen on the same trusted home network.
7. Revisit Settings later to change any wizard choice.

No Family Hub cloud account exists. No household data is hosted by the project owner.

---

## 2. Repo Strategy

The public edition must live in a **new repository with fresh history**.

### Private repo

The existing private `Family_Hub` repository remains untouched as the owner's personal version. It keeps:

- private history,
- household-specific configuration,
- personal launcher entries,
- private deployment assumptions,
- any local-only features that are useful to the owner.

### Public repo

Create a new public repository named **Family Hub** from a sanitized snapshot of current working code.

Requirements:

- Do not preserve the private repository's Git history.
- Do not include private household config, local addresses, private hostnames, personal ports, credentials, tokens, screenshots containing private data, or other deploy-specific information.
- The two repos remain independent permanently.
- Improvements may be manually copied between repos when useful, but there is no automatic synchronization requirement.
- Internet-radio work from the public edition should later be ported back to the private edition manually.
- Use an MIT license unless changed explicitly later.
- Do not optimize the repository for discovery or promotion. It may be public, but no effort is required to advertise it, publish packages broadly, or turn it into a community project.

---

## 3. Product Contract

### Core features

These are part of the basic Family Hub experience and are not user-disableable in V1 unless implementation requires a safety fallback:

- Calendar
- Clock / date
- Shopping list
- Notes
- Timers
- Kitchen reference / conversion tools

Calendar remains the primary screen anchor and must not disappear.

### Optional features

Users may enable or disable:

- Weather
- Sports
- Internet radio / music
- Commute
- Public media/app launcher

Disabled modules must not leave blank holes. The dashboard must reflow into sensible predefined layouts.

### Explicitly not included in public V1

- Private homelab launcher entries
- Custom localhost app-launcher system
- Spotify integration
- Apple Music integration
- YouTube Music integration
- Pandora integration
- iHeartRadio integration
- TuneIn integration
- Local music folders
- Drag-and-drop dashboard construction
- User accounts
- Multi-household tenancy
- Cloud hosting by the project owner
- Offline synchronization between devices
- Automatic software updates
- Backup/restore UI
- Phone-first layout
- Exhaustive device/platform certification
- Home Assistant / Jellyfin / custom homelab integration work
- Outlook / Microsoft Calendar
- Automated HTTPS/Tailscale setup

---

## 4. Architecture Principles

Preserve the existing application shape unless a phase specifically requires a narrow change:

- Flask
- Jinja templates
- HTMX
- Socket.IO
- APScheduler
- SQLite
- Provider/adaptor layers
- Server-side configuration and credentials
- Existing local data/cache model

Do not replatform to React, Electron, or another SPA framework.

The public edition should behave as a **self-hosted household server with a touch-friendly web interface**.

Windows receives the most polished local-host experience. Linux and Raspberry Pi remain supported secondary hosts. Tablets and touch displays access the same running Family Hub instance over the local network.

---

## 5. Agent Operating Rules

These rules apply to every implementation phase, especially when using capable but rotating free coding models.

1. **Inspect current repo state before editing.** Do not assume this document perfectly matches future code.
2. **Do not expand product scope.** If a missing capability is not required by the phase, do not invent it.
3. **Keep phases cohesive.** Do not split work into microscopic sub-phases simply to make a smaller model comfortable.
4. **Prefer existing architecture.** Reuse current services, providers, config, templates, tests, and styles before creating new abstractions.
5. **Do not touch the private repo.**
6. **Do not reintroduce private household values.**
7. **Do not create hosted dependencies controlled by the project owner.**
8. **Do not add auth/accounts for a trusted-home-LAN appliance.**
9. **Do not turn the dashboard into draggable Lego blocks.**
10. **Do not over-test fringe cases.** The target is reasonable happy-path confidence, not exhaustive compatibility.
11. **Keep the current automated suite green** unless a test is intentionally updated for changed public-edition behavior.
12. **Add targeted tests for new behavior**, but avoid combinatorial test matrices.
13. When a phase reveals a genuine product decision not covered here, stop and document the decision rather than silently inventing scope.

---

# Phase 1 — Public Genesis and Household-Neutral Baseline

**Status:** Planned

## Goal

Create the independent public Family Hub codebase and remove assumptions that only make sense in the private household.

## Deliverables

- Create the new public repository from a sanitized snapshot of the current private app.
- Start with fresh Git history.
- Add MIT license.
- Preserve the existing core architecture and functioning dashboard.
- Confirm safe tracked defaults in:
  - `config.example.yaml`
  - `.env.example`
  - `docs/CONFIGURATION.md`
  - `docs/DEPLOYMENT.md`
- Remove or neutralize any remaining:
  - private addresses,
  - personal hostnames,
  - LAN-specific values,
  - private ports,
  - private app names,
  - credentials,
  - tokens,
  - household-specific favorite teams,
  - screenshots or docs containing private information.
- Remove the private/local homelab app-launcher configuration and any public-facing documentation that assumes companion Flask apps on localhost ports.
- Keep normal public launcher destinations such as YouTube, ESPN, Pluto TV, and similar broadly useful services.
- Define one persistent public-edition data/config location for installed runtime state.
- Preserve current Google/ICS calendar, weather, sports, shopping, notes, timers, reference/conversion, commute, and launcher code where still useful.
- Mark unsupported attic systems as out of scope rather than trying to rehabilitate them.

## Non-Goals

- No installer yet.
- No first-run wizard yet.
- No major UI redesign.
- No PWA work.
- No music implementation beyond preserving useful provider abstractions.
- No new integrations.

## Acceptance Criteria

- Public repo contains no known private household data.
- Public repo boots using safe defaults.
- Core dashboard still renders.
- Existing automated tests remain green or have documented public-edition adjustments.
- No public UI or docs refer to the owner's private Flask apps or localhost homelab ports.
- Public and private repositories are independent.

---

# Phase 2 — Adaptive Dashboard, Persistent Settings, and First-Run Wizard

**Status:** Planned

## Goal

Make Family Hub configurable by a normal user without editing YAML or `.env`, while ensuring optional modules disappear cleanly without leaving layout holes.

This phase intentionally combines configuration UI, wizard behavior, and adaptive layout because they are one product problem.

## Deliverables

### A. Adaptive dashboard

Refactor the current fixed layout into predefined adaptive regions.

Required behavior:

- Calendar remains the main anchor.
- Core utilities remain available.
- Optional modules render only when enabled.
- Removing a module causes neighboring content to expand or move into a sensible predefined layout.
- Weather disabled + music enabled:
  - music shifts upward instead of leaving a weather-sized hole.
- Sports disabled + launcher enabled:
  - launcher settles to the bottom appropriately without reserving empty sports-ticker space.
- Commute disabled:
  - the relevant lower tile cleanly falls back to timer behavior or another defined layout.
- No drag-and-drop.
- No arbitrary user resizing.
- A few internal layout presets or CSS grid variants are acceptable if needed.

### B. Permanent Settings access

Add a small, unobtrusive **gear icon** that is always accessible regardless of whether the optional app launcher is enabled.

Settings must allow the user to revisit first-run choices later.

### C. First-run wizard

On first launch with no completed household setup, automatically enter setup.

The wizard should collect or configure:

- household/display name, optional,
- timezone,
- 12/24-hour clock preference,
- theme,
- weather location,
- calendar provider,
- optional sports,
- optional music,
- optional commute,
- optional public app launcher,
- Windows startup preference where applicable.

Do not expose raw YAML or `.env` editing.

### D. Settings persistence

Wizard and Settings must write through a safe application configuration layer rather than having template code directly manipulate arbitrary files.

Preserve advanced config files for developer/manual use, but normal users should never need them.

## Non-Goals

- No Google OAuth polish yet beyond whatever is required to reach the next phase.
- No Windows installer yet.
- No PWA yet.
- No custom dashboard-builder system.
- No user accounts.
- No phone-specific UI.

## Acceptance Criteria

- Fresh install opens the wizard.
- Completing the wizard produces a working dashboard.
- Reopening Settings allows module choices to be changed later.
- Disabling each optional major region does not leave an obvious blank hole.
- A representative "full" layout and a representative "minimal optional modules" layout both render cleanly.
- Core calendar, shopping, notes, timers, clock/date, and conversion/reference tools remain available.
- Existing tests remain green plus targeted tests for configuration persistence and adaptive rendering.

---

# Phase 3 — Household Integrations: Calendar, Weather, Sports, and Commute

**Status:** Planned

## Goal

Turn existing private-style provider configuration into friendly household onboarding for the public edition.

## Deliverables

### A. Google Calendar

Support:

- Google Calendar OAuth,
- ICS calendar feeds.

Public Google OAuth should use the Family Hub OAuth application rather than requiring friends to create their own Google Cloud project.

Expected user experience:

1. Choose Google Calendar.
2. Click **Connect Google Calendar**.
3. Browser opens Google's authorization flow.
4. User may see Google's one-time unverified/personal-use warning.
5. User authorizes Family Hub.
6. Tokens are stored locally on their own host.
7. Family Hub uses the selected calendar(s).

The Google project should be configured for production/personal-use rather than a seven-day testing-token workflow.

Do not attempt full public OAuth verification in this phase.

### B. Weather

- Keep Open-Meteo or current safe provider as the default.
- Let the user choose a friendly city/location without manually entering coordinates where practical.
- Weather is optional.
- Disabled weather must collapse cleanly through Phase 2's layout system.

### C. Sports

Provide a useful-but-bounded sports picker.

Primary supported leagues:

- NFL
- MLB
- NBA
- NHL
- MLS
- NCAA football
- NCAA basketball

Also support a limited **major events** category when data is reasonably available through current/public providers.

Examples of desirable major-event ticker coverage:

- The Masters and similarly significant PGA majors
- Wimbledon
- U.S. Open tennis
- Australian Open
- French Open
- Olympics

For special events, keep coverage intentionally lightweight:

- top headlines,
- major result/status,
- top few leaderboard positions when appropriate,
- no attempt to become a full sports application.

Do not add obscure leagues or events merely because a provider exposes them.

### D. Commute

- Commute remains optional.
- User can enter home/work locations through Settings.
- Provider credentials stay server-side.
- If disabled or outside configured use conditions, the dashboard falls back cleanly to its non-commute state.
- Preserve privacy boundary: tablet/browser clients should not need raw stored addresses.

## Non-Goals

- No Outlook/Microsoft Calendar.
- No full sports site.
- No complete golf/tennis leaderboards.
- No fantasy sports.
- No cloud sync service.
- No multi-household support.

## Acceptance Criteria

- Google authorization completes from a clean public install.
- Google Calendar can read events; existing write behavior should remain if already supported.
- ICS works as a no-OAuth alternative.
- Weather can be configured without editing files.
- User can choose major U.S. teams/leagues plus NCAA.
- Major-event support is bounded and does not distort the ticker when unavailable.
- Commute can be enabled/disabled through Settings.
- Disabled integrations do not produce broken or empty UI shells.
- Targeted integration/config tests pass.

---

# Phase 4 — Internet Radio and Public Media Launcher

**Status:** Planned

## Goal

Provide useful music without Spotify or other commercial-service developer-account friction, and preserve a clean public media launcher without private homelab baggage.

## Deliverables

### A. Internet radio

Turn the existing Radio Browser and SomaFM provider skeletons into real usable music sources.

Supported V1 music:

- Radio Browser station search/browse
- SomaFM curated stations
- Saved/favorite stations
- Optional custom direct stream URL if simple and reliable

Expected player behavior:

- play/pause,
- station title,
- current station/source,
- basic volume control if appropriate,
- graceful failure when a station stream is dead or unsupported.

Do not assume every community station URL is permanent.

### B. Music UX

Music is optional.

If enabled:

- present radio as the default account-free music experience,
- avoid exposing implementation/provider complexity unnecessarily.

If disabled:

- music surfaces disappear and the layout reflows.

### C. Public media launcher

Keep the broadly useful launcher concept.

Allowed default examples:

- YouTube
- ESPN
- Pluto TV
- other broadly useful streaming/web destinations already present and appropriate

Remove:

- owner's localhost Flask applications,
- custom homelab ports,
- private companion app labels,
- "add your own homelab service" functionality for V1.

The public launcher is curated, not a custom-homelab platform.

### D. Private-repo follow-up

After this phase works in the public edition, manually port the internet-radio provider improvements back into the owner's private Family Hub repo.

Do not couple the repos.

## Non-Goals

- No Spotify.
- No Apple Music.
- No YouTube Music integration.
- No Pandora.
- No iHeartRadio.
- No TuneIn integration.
- No local music folder support.
- No custom homelab-app builder.

## Acceptance Criteria

- Several Radio Browser stations play successfully.
- Several SomaFM stations play successfully.
- One deliberately dead/bad station fails gracefully rather than breaking the player.
- Music can be disabled without a layout hole.
- Public launcher contains no private/local Flask app assumptions.
- Launcher still behaves sensibly in kiosk/large-screen use.
- Targeted provider/player tests pass.

---

# Phase 5 — Touch, Tablet Access, LAN Hosting, and PWA Basics

**Status:** Planned

## Goal

Make Family Hub feel natural on a touchscreen and make it simple for a user to open the same household Hub on an iPad or Android tablet.

## Deliverables

### A. Touch-first pass

Audit interactive targets and remove mouse-only assumptions.

Focus especially on:

- calendar event chips,
- navigation controls,
- shopping,
- notes,
- timers,
- conversion/reference tools,
- settings,
- modal buttons,
- text inputs,
- scrolling,
- accidental text selection,
- hover-only affordances.

Target approximately 44–48px interactive areas where practical without destroying calendar density.

Desktop mouse use must continue to work.

### B. LAN server behavior

Windows/Linux host must be able to serve Family Hub to other devices on the same trusted home network.

No login screen is required.

### C. Windows Firewall behavior

Windows setup should create or request the narrow firewall permission needed for local tablet access on private networks.

User-facing wording should explain the actual intended benefit, for example:

> **Allow tablet access**  
> This lets your iPad or Android tablet connect to Family Hub while both devices are on your home Wi-Fi.

Avoid vague wording such as "allows devices on your network."

### D. QR connection helper

Add a Settings surface such as:

**Use Family Hub on another screen**

Show:

- detected local Family Hub address,
- QR code,
- short iPad instructions,
- short Android/tablet instructions.

### E. PWA basics

Add:

- web app manifest,
- Family Hub name,
- theme/background colors,
- app icons,
- favicon,
- standalone display metadata.

Provide home-screen/add-to-home instructions where supported.

Do **not** make automatic trusted HTTPS a V1 requirement.

Plain LAN browser/tablet access is acceptable for the friend beta. Full installability may vary by platform/browser when using local HTTP.

### F. Offline behavior

If internet access fails but the Family Hub host remains available:

- shopping remains usable,
- notes remain usable,
- timers remain usable,
- cached provider data may remain visible with stale/error treatment.

If the host itself is unavailable, clients may simply show that Family Hub cannot be reached.

No cross-device offline synchronization.

## Non-Goals

- No phone-first redesign.
- No automatic Tailscale setup.
- No automatic certificate authority.
- No cloud relay.
- No internet exposure.
- No offline-sync engine.
- No exhaustive tablet/browser certification.

## Acceptance Criteria

- Normal desktop interaction still works.
- Major controls are practical on touch.
- One representative tablet-sized viewport renders cleanly.
- A tablet on the same LAN can reach the Windows/Linux host.
- QR helper points to the correct local address in the supported normal case.
- Firewall messaging explicitly explains tablet access.
- Manifest/favicon/app icon are present.
- Basic Add-to-Home/PWA guidance exists.
- Internet outage does not break local shopping/notes/timers.

---

# Phase 6 — Windows Appliance Packaging and Secondary Linux/Pi Deployment

**Status:** Planned

## Goal

Make Windows installation and normal daily launching require no Python or Git knowledge while preserving Family Hub as a normal self-hosted web application for secondary hosts.

## Deliverables

### A. Windows installer

Produce a downloadable installer, e.g.:

`FamilyHub-Setup.exe`

The user should not need:

- Python,
- Git,
- pip,
- a virtual environment,
- command-line startup.

Installer should provide:

- Family Hub application files/runtime,
- Start Menu shortcut,
- desktop shortcut,
- Family Hub icon,
- uninstall support,
- persistent user data/config location separate from application files.

Unsigned beta builds may trigger Windows SmartScreen / unknown-publisher warnings. Document the expected **More info → Run anyway** flow rather than purchasing signing infrastructure for this hobby release.

### B. Windows host and desktop shell

The normal Windows experience should be:

1. Double-click Family Hub.
2. Hidden/local host starts if needed.
3. Family Hub UI opens.
4. Closing the visible window does not necessarily stop household hosting.
5. Host remains available from the notification tray.
6. Tray menu includes at minimum:
   - Open Family Hub
   - Settings or Open Settings
   - Quit Family Hub

**Quit Family Hub** stops the local host.

Use a thin native/WebView-style shell or equivalent approach that preserves the existing web frontend and presents Family Hub with its own application identity/icon rather than as a generic Edge taskbar window.

Do not rewrite the frontend as a native desktop app.

### C. Startup option

First-run/setup may offer:

**Start Family Hub with Windows**

This is optional.

Do **not** add a "keep this PC awake" setting.

### D. Manual upgrades

V1 updates are manual.

Expected flow:

1. User downloads a newer installer.
2. Runs it.
3. Application files update.
4. Household config/data remains intact.

No automatic update daemon.

### E. Linux / Raspberry Pi

Keep a secondary self-hosted path for:

- Debian/Ubuntu,
- Raspberry Pi OS or similar Linux.

Provide simple documented commands or a lightweight install script/container only if it materially reduces friction.

The supported claim should be modest:

- Windows is primary.
- Linux/Pi is best-effort secondary.
- A Debian VM/WSL validation is sufficient before beta if no physical Pi is available.
- Do not claim a physical Raspberry Pi was tested unless it actually was.

## Non-Goals

- No Microsoft Store publication.
- No paid code-signing requirement.
- No automatic updater.
- No NAS-specific certification.
- No Docker/NAS matrix.
- No macOS packaging.
- No mobile native app.

## Acceptance Criteria

- One normal Windows 10/11 install path works without Python/Git.
- Desktop shortcut launches Family Hub.
- Family Hub has its own icon/identity.
- Tray host behavior works.
- Optional startup behavior works.
- Quit actually stops the host.
- Upgrade/install-over preserves household state in the normal tested path.
- Debian/Linux secondary launch works in one available test environment.
- Linux/Pi documentation clearly labels best-effort status.

---

# Phase 7 — Beta Handoff, Minimal QA, Documentation, and Release

**Status:** Planned

## Goal

Stop building when the normal friend experience works. Package the project so invited users can install it without needing a personal walkthrough for every step.

This is intentionally **not** a production-hardening phase.

## Deliverables

### A. README for normal humans

Top of README should explain:

- what Family Hub is,
- screenshot,
- that it is self-hosted,
- that household data stays on the user's own host,
- Windows download path,
- basic tablet connection concept,
- Linux/Pi secondary path,
- hobby/best-effort status.

The first instructions should not be Git clone commands.

### B. Simple install guide

Windows:

1. Download installer.
2. If Windows SmartScreen warns, use **More info → Run anyway**.
3. Complete setup wizard.
4. Connect Google Calendar if desired.
5. Open Family Hub.

Tablet:

1. Open Family Hub Settings.
2. Choose **Use Family Hub on another screen**.
3. Scan QR code.
4. Follow the shown iPad/Android home-screen instructions.

Linux/Pi:

- concise secondary-host instructions,
- clearly marked best effort.

### C. Project expectations

Include a short statement similar to:

> Family Hub is a hobby project shared as-is for friends-and-family use. The documented normal configurations are tested on a best-effort basis. Other setups may work but are not guaranteed. Issues and pull requests are welcome, but there are no support or response-time commitments.

GitHub issues/PRs may remain enabled, but there is no requirement for the owner to operate the repo as a support desk.

### D. Minimal happy-path QA

Required before friend beta:

- current automated test suite passes,
- targeted tests for new public-edition behavior pass,
- one normal Windows install,
- one normal Windows launch,
- one tray-close/reopen/quit flow,
- one startup/reboot check if practical,
- one Google Calendar authorization,
- one calendar read/write sanity check if write support is retained,
- one weather setup,
- one sports setup,
- one internet-radio playback check,
- one representative touch/tablet viewport check,
- one same-LAN tablet/browser connection,
- one adaptive-layout check with several optional modules disabled,
- one Linux/Debian secondary-host smoke test if available.

Not required:

- every module toggle combination,
- every browser,
- every NAS vendor,
- every Windows build,
- every antivirus product,
- every tablet model,
- weird drive-letter/path combinations,
- obscure network arrangements,
- fringe compatibility investigations unless a problem affects the normal supported path.

### E. Beta release

Publish an initial friend-facing beta release rather than calling it 1.0.

Example:

`Family Hub 0.1 Beta`

Attach the Windows installer and concise release notes.

## Non-Goals

- No "production readiness" certification.
- No exhaustive performance testing.
- No long-term support promise.
- No telemetry.
- No analytics.
- No crash-reporting backend operated by the owner.
- No broad marketing/discovery campaign.
- No requirement to fix every reported issue before release.

## Acceptance Criteria

A reasonably technical but non-developer friend can:

1. find the release,
2. download the Windows installer,
3. install it,
4. complete setup,
5. see a working Family Hub,
6. connect a tablet on the same home network using the provided instructions,
7. use the core features without touching Python, Git, YAML, or `.env`.

At that point the beta is considered complete.

---

# 6. Testing Philosophy

Family Hub Public Edition is a **generosity project**, not a commercial software obligation.

The testing target is:

> **Reasonable confidence that the documented normal path works.**

It is not:

> **Proof that Family Hub behaves correctly under every unusual machine, filesystem, browser, network, antivirus, NAS, display, driver, or historical-software combination.**

When a fringe bug appears after beta:

- fix it later if it is easy and useful,
- document it if necessary,
- or leave it as a known limitation.

A fringe issue should not automatically block a phase or release.

---

# 7. Scope-Creep Guardrails

Before accepting new work, ask:

1. Does this help a friend install Family Hub?
2. Does this help a friend configure Family Hub?
3. Does this make the large-screen/touch experience materially better?
4. Does this make normal local hosting more reliable?
5. Is it required by a current supported integration?

If the answer is no, it probably does not belong in the beta.

Examples that should normally be deferred:

- Outlook because "someone might use it someday"
- Apple Music because it exists
- custom dashboard widgets
- smart-home discovery
- profiles
- household accounts
- cloud sync
- remote internet access
- automatic HTTPS
- phone-specific redesign
- NAS vendor-specific installers
- backup systems
- self-healing services
- automatic update infrastructure

The private Family Hub already demonstrated how easily useful appliance software can accumulate attic systems. The public edition should remain deliberately narrower.

---

# 8. Expected Work Shape

This plan intentionally uses **seven substantial phases**, not dozens of micro-phases.

A capable coding agent should normally receive an entire phase or a cohesive segment within a phase, inspect the repository, implement the work, run relevant tests, and report:

- files changed,
- behavior implemented,
- tests run,
- known limitations,
- anything deferred because it would expand scope.

The goal is not to make each phase small enough for a tiny model. The goal is to make each phase coherent enough that a capable rotating free coding model can execute it without having to infer the product.

---

# 9. Definition of Done for the Public-Edition Project

The project is done when:

- the public repo is clean and household-agnostic,
- a friend can install it on Windows without developer tooling,
- first-run setup is understandable,
- Calendar is functional,
- core household tools work,
- optional modules reflow cleanly,
- weather/sports/commute are configurable,
- internet radio provides account-free music,
- the public launcher contains only broadly useful destinations,
- touchscreen use is practical,
- a tablet can connect over the trusted home LAN,
- Family Hub has its own app identity/icon,
- Windows tray/startup behavior is usable,
- Linux/Pi has a reasonable secondary path,
- documentation explains the normal path,
- normal-path smoke testing passes,
- and no one involved feels obligated to turn it into a commercial support project.

Anything beyond that is future work only if it is actually worth doing.
