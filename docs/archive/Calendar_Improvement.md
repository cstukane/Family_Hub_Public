**Goal:** Add support for a second Google Calendar feed (spouse) to the existing Family Hub calendar integration. Fetch events from both calendars, merge them into a single unified list for the UI/scheduler, and deduplicate events that appear on both calendars (invites accepted by both). The dedupe rule should keep the event from the “owner/creator” and drop the attendee copy.

### 1) First: repo review + current behavior audit = COMPLETE

1. Locate the existing Google Calendar integration code:

   * Where credentials are loaded
   * Where tokens are stored/refreshed
   * Where events are fetched (API call code)
   * Where events are normalized into your internal event model
   * Where events are color-coded by “owner/original creator” (already exists in UI chips)
2. Summarize:

   * What auth method is used (OAuth client + token.json, service account, etc.)
   * Current config mechanism (`.env`, config file, hardcoded path, etc.)
   * Current fetch window (yesterday → next N days) and refresh cadence
   * The internal “Event” schema used by the app (fields available: id, start/end, summary, organizer, creator, iCalUID, etc.)

### 2) Credentials + configuration requirements = COMPLETE

Implement a clean way to add the spouse calendar credentials without breaking the existing one.

**Do not assume** my existing structure — detect it and follow the existing style:

* If the project uses `.env`, add variables like:

  * `GCAL_PRIMARY_CREDENTIALS_PATH=...`
  * `GCAL_SPOUSE_CREDENTIALS_PATH=...`
  * `GCAL_PRIMARY_TOKEN_PATH=...`
  * `GCAL_SPOUSE_TOKEN_PATH=...`
  * or a single `GCAL_ACCOUNTS_JSON=...` pattern (if better)
* If the project stores secrets in a `/secrets` folder, follow that.
* Update README / setup docs with exact steps: where to put credential JSON(s), where token(s) go, and how to run first-time auth for each.

**Important:** We are using TWO OAuth identities (mine + spouse), not just multiple calendar IDs from one account (unless the repo is already built differently). The solution must support separate tokens per account.

### 3) Fetching strategy (sequential first, async optional)

* Implement fetching events from both calendars for the same time window.
* Default to sequential fetching (simple/reliable).
* If the app already uses async (FastAPI/asyncio/etc.), implement concurrent fetching safely (e.g., `asyncio.gather`) and keep rate limits reasonable.
* Add caching behavior consistent with the current app (if any) so we’re not hammering the API.

### 4) Merge + normalize events into one unified list = COMPLETE

* After fetching both sets, normalize them into a single unified internal model that the UI already consumes.
* Ensure timezone normalization matches existing behavior.

### 5) Deduplication rule (critical) = COMPLETE

We need to avoid duplicates when the same real-world event exists on both calendars because one user invited the other and the invite was accepted.

**Key behavior desired:**

* If event A appears on both calendars and **I am the owner/creator/organizer**, keep *my* version and drop spouse’s duplicate.
* If spouse is the owner/creator/organizer, keep spouse’s version and drop mine.
* Owner precedence is based on whichever fields the app already uses for “owner color-coding.”

**How to reliably identify duplicates:**

1. Prefer using a stable shared identifier:

   * `iCalUID` is often shared across attendees (good dedupe key)
   * If the current internal model includes it, use it as primary dedupe key
2. If `iCalUID` isn’t available, fallback to a composite fingerprint:

   * normalized title/summary
   * start time
   * end time (or duration)
   * location (optional)
   * and a small time tolerance (e.g., +/- 1 minute) for API rounding issues

**Dedupe algorithm:**

* Group events by the dedupe key.
* For each group with >1 event:

  * Determine “primary” event by:

    * organizer/creator precedence (match current “owner” logic already used for chip coloring)
    * If both are ambiguous, choose deterministic tie-break:

      * prefer organizer != null
      * else prefer creator email matching configured “primary user”
      * else keep the one from the primary calendar source
  * Keep the primary event and drop others.
* Preserve provenance metadata so UI still knows which account(s) had the event, even if deduped (optional but ideal):

  * e.g., `sources: ["primary","spouse"]` plus `kept_from: "primary"`

### 6) UI impact

* Confirm unified list renders correctly without duplicates.
* Keep existing color-coding by owner/creator.
* If you add provenance metadata, optionally add a subtle indicator (only if it’s easy) that the event exists on both calendars.

### 7) Tests / validation steps

Add minimal tests (or at least a dev-only diagnostic) that proves:

* Same event on both calendars results in one UI chip.
* Ownership precedence works:

  * A created-by-me event shared with spouse keeps mine.
  * A created-by-spouse shared with me keeps spouse’s.
* Non-overlapping events still show from both calendars.
* Token/credential separation works (two different accounts).

### 8) Deliverables

* Code changes implementing multi-account calendar fetch, merge, dedupe.
* Updated config/secrets instructions.
* Any new `.env` variables documented.
* If needed, add a small command/script to perform first-time auth for each account (e.g., `python auth_primary.py`, `python auth_spouse.py`) consistent with the repo’s structure.
