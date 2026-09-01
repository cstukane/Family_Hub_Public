# Product & Architecture Review — Family Hub

*Historical review written 2026-07-02. The privacy and runtime-attic findings described below were resolved in the 2026-08 convergence pass; retain the details as decision context, not current-state guidance.

*Original scope: Scope: whole-product judgment against the stated identity — a local-first, always-on kitchen TV dashboard and front door to a personal homelab. Not a code review. Read alongside `PRODUCT_DIRECTION.md` (2026-06-11), which this review largely audits three weeks of progress against.*

---

## 1. The verdict

**The repo is converging, and faster than most personal projects ever manage.** Since the June 11 direction pass you have: deleted four attic subsystems (news, edge, self-heal, metrics) with a written reachability audit to justify it, rewritten the README to describe the app that actually exists (including an explicit "attic" section — rare honesty), committed the redesign, fixed the miniplayer's disconnected state, and shipped staleness indicators on the commute tile and center zone. That is real convergence work, executed in order.

But the convergence is **half-finished in exactly the places that matter most**, and there are three concrete signs of gravity pulling the other way:

1. **The trust pass stalled at two tiles out of five.** Commute and the center zone show "last updated"; weather, calendar/Up Next, and the sports ticker do not. The single highest-leverage item from the direction doc is 40% done.
2. **`docs/ROADMAP.md` actively contradicts `PRODUCT_DIRECTION.md`.** The roadmap lists profiles & presence, local voice wake word (Porcupine + Whisper), and automatic update scheduling — three items the direction doc explicitly put on the not-list. Two direction documents disagreeing is worse than one being wrong, because future work (human or model) will pick whichever one justifies what it wants to build.
3. **The attic is "frozen" on paper but running in production.** The scheduler still executes update checks, webhook status checks, and casting discovery every cycle; `config.yaml` still says `iot.enabled: true`, `casting.enabled: true`, and carries an `active: true` webhook pointed at `example.com`. Frozen code that executes isn't frozen — it's unattended.

The single most urgent finding, though, is not architectural. It's **privacy**: `config.yaml` is committed to git containing your home street address, work street address, LAN IP, and Tailscale hostname, and the README repeats the home/work addresses verbatim. See §5.

So: yes, your instinct is right. The next broad direction should be the trust/surface-slimming pass. But reorder it — privacy hygiene first (an evening), finish the staleness pattern second, then make "frozen" mean "off at runtime," and only then delete code.

---

## 2. Is the product identity clear?

**In the flagship docs, yes — unusually so.** README and PRODUCT_DIRECTION.md tell the same story in the same words: glance in 3 seconds, occasionally touch, sibling apps get the new functionality. The "personal appliance, not a platform" framing is stated, restated, and mostly enforced.

**In the repo as a whole, there are still three competing sources of truth:**

- **PRODUCT_DIRECTION.md** says: converge, no new features, attic is frozen.
- **docs/ROADMAP.md** says: profiles & presence strip, settings phases, voice wake word, auto-update scheduling. This is the old expansionist roadmap, un-updated. The direction doc even warns readers not to trust it (§8) — but a warning buried in another file doesn't defuse it. **Fix or delete the roadmap; don't leave a second steering wheel in the car.**
- **config.yaml** says: IoT enabled, casting enabled with auto-discovery, a live webhook, chores config carried while disabled, placeholder `family:` members (dad@example.com). Config is supposed to be ground truth for what's deployed; right now it's ground truth plus wishes plus fossils.

Also worth naming: the repo still carries identity residue — `hub_ui/` (a dead second frontend whose index.html still promises a news ticker), `rebrand.txt`, `Port_Reference.txt`, `docs/KITCHEN_HUB_PLAN.md`, and ~28 docs of which maybe 8 are load-bearing. None of this breaks anything, but every stale file is a chance for a future contributor (or a future Claude session) to resurrect a dead direction. The June cleanup deleted dead *code*; dead *narrative* got a lighter pass.

## 3. Does the architecture fit a kitchen kiosk?

**Yes. Don't touch the shape.** APScheduler → adapter → SQLite TTL cache → service → HTMX/Socket.IO is close to the platonic ideal for this product: server-rendered, cache-on-disk so a reboot comes back warm, no build step, no client framework to age out, real-time only where it earns it (timers, up-next, scores). The adapter pattern is pulling its weight — you actually swapped sports providers, which is the test most "swappable adapter" architectures never face.

Two architecture-adjacent concerns, both about *load* rather than *shape*:

- **The two megafiles are still growing.** `hub/routes/api.py` was 51KB when CLAUDE.md was written; it's 64KB now. `api_media_admin.py` sits at 91KB. The direction doc's call — don't refactor, but *stop adding* — is being violated by drift, not decision. A kiosk this size should not have a 91KB route file for its admin/media surface; that file alone is a signal that the media-launcher subsystem is carrying platform ambitions. You don't need to split it this quarter. You do need the additions to stop.
- **The scheduler runs eight job families for a five-tile product.** Calendar, weather, sports, cache cleanup: core. Update check, webhook status check, weather-alert monitor, casting discovery: attic executing on the appliance. Every background job is a way for the wall to be wrong or wedged. The cheapest resilience win available is subtraction (see §6).

One genuinely good recent decision to call out: deleting self-healing and answering kiosk resilience with "systemd restart + cache on disk" is exactly the appliance mindset. Resist any future temptation to re-add watchdog cleverness.

## 4. Overbuilt — the attic, three weeks on

The June cleanup was real: news service, edge computing, self-heal, and metrics are gone, and `ATTIC_REACHABILITY_AUDIT.md` is a model of how to do this safely. Credit where due.

What remains, and what I'd say about each:

| Subsystem | State | Judgment |
|---|---|---|
| IoT / Home Assistant / Alexa / Google Home / Roku adapters | `enabled: true` in config, zero dashboard surface | The clearest "becoming Command Center" risk in the repo. Disable in config now; delete adapters when they next cause friction. Smart-home control belongs in a sibling app if it belongs anywhere. |
| Casting (`casting.py`, 15KB + scheduler discovery job) | Auto-discovery running every 5 min | Turn the discovery job off. Network scanning from the kiosk for a feature with no UI is pure liability. |
| Webhooks (20KB + mgmt UI + scheduler job) | One `active: true` webhook to `example.com` | A webhook platform for one house. Deactivate the config entry, drop the scheduler job. |
| `update.py` (16KB + daily job) | Roadmap wants to *expand* it | A kiosk updates via `git pull` + restart, as the README now correctly says. Remove the daily job; the roadmap item should die. |
| Plugins (route file + 4 modules + migrations) | No real plugin exists | Frozen is fine; the plugin *route file* being registered is the part I'd retire first. |
| Backup, chores, voice, cooking/photos/ambient views | Disabled or dormant | Fine to carry short-term. Chores deserves the direction doc's test: usage decides, not code. Ambient is the only one with a live claim on the future (§7). |
| `hub/adapters/news_aggregator.py` | Orphan — news was "removed 2026-06-15" | The cleanup missed it. Delete; it's the kind of remnant that re-seeds a dead feature. |
| `hub_ui/` | Dead parallel frontend | Delete. Two UIs is one identity too many. |

The pattern worth internalizing: **your attic problem is no longer code volume, it's runtime and config surface.** ~Half the config schema (`hub/config.py`) validates subsystems the product doesn't have. Every one of those sections is a place where a future settings UI, a future doc, or a future AI pass will find "evidence" the feature is real.

## 5. Underbuilt for family trust

This is where the honest answer is "yes, and you already know it — finish the list you wrote."

**a) Staleness is 2/5 done.** Commute tile: has "Updated 7:08 PM (stale)". Center zone: has "Last updated". Weather panel, Up Next/calendar, sports ticker: nothing. The pattern exists, the cache knows fetch times, the remaining work is application, not invention. This is the highest-value unfinished work in the repo. A stale weather tile at 6am is precisely the "wall is wrong" failure that erodes the family's trust silently.

**b) The Google token expiry path is still the most likely real-world failure with no designed UX.** "Calendar can't sync — tap to reconnect" beats an empty week grid. Make this one path excellent; don't generalize a failure-state framework out of it.

**c) Privacy — the finding that outranks everything else in this review:**

- `config.yaml` is **tracked in git** and contains your home street address, work street address, your LAN IP (`192.0.2.10`), and your Tailscale machine name (`hub.example.internal` in the SSL cert path).
- **README.md repeats the home and work addresses** in its example config block.
- These are in git *history*, not just HEAD, so if this repo is or ever becomes public (or is cloned to any service), scrubbing HEAD isn't enough.

Recommended shape (an evening of work): commit a `config.example.yaml` with placeholder values; move the real `config.yaml` out of tracking (gitignore it, keep it in `instance/` or the deploy host); scrub the README examples; then decide whether history rewrite matters based on the repo's visibility. Note the app-side exposure is actually handled well — `/api/config` filters to features/ui/layout — the leak is the *repo*, not the server.

**d) What's NOT underbuilt** (don't add): auth for the LAN kiosk, multi-user profiles, self-healing, monitoring. `features.auth: false` on a trusted home LAN is the right call for an appliance. Adding login friction to a kitchen wall would damage the product more than any threat it mitigates.

## 6. Config/implementation alignment

Partially aligned, and the misalignments are all in one direction — config claims more than the product delivers:

- `iot.enabled: true`, `casting.enabled: true` + discovery — no dashboard surface for either.
- An `active: true` webhook to `example.com` — attic config that *executes*.
- `family:` block with `dad@example.com` placeholders — either wire real emails to the calendar color-coding (which the git history says exists) or drop the block.
- `music.providers` (radio_browser, somafm, podcast_index) all disabled — three provider integrations for features the miniplayer doesn't surface. Attic.
- Windows-specific SSL cert paths in a config whose deploy story is Linux/systemd — a small tell that dev-machine state is leaking into the canonical config.

The direction doc's rule — "config.yaml is ground truth and beats the docs" — only works if config is *curated*. Right now it needs the same honesty pass the README got.

## 7. The roadmap question

`docs/ROADMAP.md` is pointed at **divergence** and should be rewritten this week — it's a one-file fix with outsized protective value. Concretely, the mid/long-term list re-opens three doors the direction doc closed:

- **Profiles & presence strip** — this is Family OS gravity. Say no until a family member asks for it by name.
- **Local voice (wake word + STT)** — an always-listening microphone is a different *product category* (and a different trust conversation with the family) than a glanceable wall. If voice ever happens, it's a sibling service that calls the hub's API, not a hub feature.
- **Automatic update scheduling** — contradicts the already-made decision that kiosks update via `git pull` + restart.

A convergent roadmap for the next few phases, in order:

1. **Privacy/repo hygiene** (§5c) — smallest, most irreversible-if-ignored.
2. **Finish the staleness pattern** on weather, Up Next, and ticker; design the Google-token-expiry state.
3. **Runtime attic shutdown** — flip iot/casting/webhook config off, remove the update/webhook/casting scheduler jobs. Deletion of the code can trail by months; being *off* is the win.
4. **Narrative cleanup** — rewrite ROADMAP.md, delete `hub_ui/`, `news_aggregator.py`, `rebrand.txt`, and archive the ~15 superseded docs into `docs/archive/` (or delete; git remembers).
5. **Only then**: the ambient/dead-zone experiment from PRODUCT_DIRECTION §7.4, reusing existing photos/ambient code.

## 8. Assumptions you're making that may be wrong

- **"The family touches the screen."** The whole "add milk" investment assumes non-builder usage that I can't verify from the repo and you may not have verified in the kitchen. Before polishing touch flows further, spend a week just noticing: does anyone but you touch it? If the honest answer is no, the product is a *pure glance* appliance and the roadmap simplifies further (and shopping might live better in a phone-reachable sibling app that the hub merely displays).
- **"Sibling apps solve the growth problem."** Twelve companion apps on twelve ports is itself a surface. The hub's launcher currently assumes they're all up; a dead port is a dead button, which is a trust failure *on the hub* even though the fault is elsewhere. The federation strategy is right, but it makes launcher reliability the hub's problem (see §9).
- **"The week grid is the right resting view."** The direction doc already flagged this (the 95% ambient vs 5% planning tension). The June 17 weather modal — 240 lines of richer forecasts behind a tap — quietly bet more on the *interactive* dashboard. It's a defensible feature, but notice the direction: detail-on-demand is Command Center's growth pattern. The appliance pattern is *better resting state*, not deeper drill-ins.
- **"Frozen is safe."** Frozen code with `enabled: true` config and live scheduler jobs isn't frozen, it's unsupervised. This assumption is the root of §6.
- **"The docs help future work."** The good docs (README, PRODUCT_DIRECTION, the attic audit) genuinely do — they're better than what most funded teams maintain. But 28 docs with maybe 8 current means any given reader has ~30% odds of steering by a dead plan. Doc *count* is now a liability the same way code count was in June.

## 9. What to absolutely not build yet

- Ambient/photo resting view — not until trust items 1–3 land. (It's the *next* right thing, which is exactly why it's tempting too early.)
- Profiles, presence, or anything per-person beyond calendar colors.
- Voice, in any form, on the hub itself.
- Any new provider, panel, or tile. The weather modal should be the last drill-in for a while.
- Settings UI phases 1–2 from the old roadmap — a 42KB settings template for a one-admin appliance is already generous.
- Route-file refactors, framework changes, auth. (Still correct to defer, per the direction doc.)

## 10. Questions to answer before committing the next phases

1. **Is this repo public, or could it become so?** Determines whether §5c is "gitignore and move on" or "history rewrite."
2. **Does anyone besides you touch the screen in a typical week?** Determines whether shopping/timers polish or pure-glance ambient work is the higher-value track.
3. **Which of the 12 sibling apps are actually alive and used?** The launcher should show only real destinations; a launcher where half the buttons 404 trains the family to ignore it.
4. **What's the actual failure log?** Before designing failure states, check `journalctl` for what has *really* broken in the last 90 days (token expiry? Open-Meteo flakes? Socket.IO wedges?). Design for the observed top two, not the imagined taxonomy.
5. **Does chores get a tile or get deleted?** It's been `enabled: false` long enough to answer by revealed preference.

## 11. Feature suggestions (deliberately few)

Only two ideas clear the bar of "serves the existing loop without adding surface":

- **Launcher health dots.** A tiny liveness check (does the port answer?) on the homelab app bar, rendering dead apps dimmed. This is the one place where a *small* addition directly serves the "front door to the homelab" half of the identity, and it converts the sibling-app strategy's main weakness (§8) into a strength. It's a glance feature, not a control feature — keep it to a dot, not a status page.
- **A single hub self-status glyph.** One small indicator (e.g., in a corner): green if all scheduler jobs succeeded on their last run, amber otherwise, tap for a one-line reason. This is the appliance-grade replacement for the deleted metrics system — the family never needs it, but *you* stop needing to SSH in to wonder.

Everything else I considered (meal planning, packages tile, school lunch menus, transit) fails the test: each is a sibling app, or nothing.

## 12. Closing judgment

Family Hub is one of the rare personal projects that wrote down what it is, noticed it had overbuilt, and then actually deleted things. The architecture fits the appliance. The identity is clear where it counts. The risk is no longer "becomes a platform by ambition" — the direction docs have killed that — it's **"stays a platform by inertia"**: enabled-but-unsurfaced config, scheduler jobs for frozen features, a contradictory roadmap, and two route files that grow because they're where the code already is.

The trust/slimming pass you proposed is the right next move. Sharpen it in three ways: put the privacy scrub first because it's the only item that gets *worse* with time; treat "frozen" as a runtime property (off) rather than a documentation property (labeled); and fix ROADMAP.md before any new session reads it. Do those, finish the staleness pattern, and the wall earns the only metric this product has: the family never doubts it.
