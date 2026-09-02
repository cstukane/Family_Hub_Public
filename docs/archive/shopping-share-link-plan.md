# Shopping Share Link Plan

## Summary

Add a single high-leverage viral feature to Family Hub: an expiring, read-only shopping list share link that a family member can open on their phone while shopping. The shared page should be live rather than snapshot-based, so it always reflects the current shopping list state until the link expires. The feature should fit the existing Family Hub surface area, reuse current Flask + HTMX patterns, avoid new infrastructure, and keep engineering scope intentionally small.

This feature is intended for low-scope household sharing, not external collaboration or multi-user editing. The link should expose only active shopping items, require no login, expire automatically, and be signed so it cannot be forged.

## Why This Feature

The current repo signals suggest the strongest shareable moment is the shopping workflow:

- Shopping already has a well-defined CRUD loop in the existing app surface.
- The shopping list is accessible from the sidebar and its own modal, making it a natural entry point for a share action.
- Cooking mode already feeds users into shopping through the existing "Add Ingredients to Shopping" action, which increases the chance that a user wants to send the list to someone leaving for the store.
- This moment is inherently social and practical: one person curates the list on the household screen, another person consumes it on a phone in the real world.

Compared with invites, referrals, or broader social features, a shopping share link is much smaller in scope, aligns with the current product, and produces a measurable loop without introducing a new growth system.

## Assumptions and Constraints

- The share link is live, not a snapshot.
- The share link is read-only.
- The share link expires automatically after a fixed TTL.
- The initial TTL should be 24 hours unless implementation constraints strongly justify a different short-lived default.
- The shared page should show active shopping items only (`done == false`).
- No new database tables should be introduced for this feature.
- No new auth system should be introduced.
- No new analytics framework should be introduced.
- Existing Flask routes, SQLite access patterns, and lightweight templates should be reused.
- Audit logging should be used for feature measurement.
- The feature should remain LAN-friendly and privacy-conscious, consistent with the app's existing deployment model.

## Implementation Details

### 1. UI Entry Point

Add a `Share List` action to the existing shopping modal.

Expected behavior:

- The action should appear in the current shopping modal rather than introducing a new modal stack or navigation pattern.
- Clicking it should request a new share link from the backend.
- On success, the UI should reveal:
  - the generated URL
  - a copy action
  - the link expiry time
- If clipboard copy succeeds, show a success state using existing toast behavior if available.
- If clipboard copy is unavailable, fall back to a selectable text field so the user can manually copy the link.

The share action should be implemented in a way that matches the current UI style and avoids any new design system or growth-specific UI pattern.

### 2. Backend API

Add a new endpoint:

- `POST /api/shopping/share-link`

Responsibilities:

- Generate a signed, expiring token for a shopping share link.
- Build and return an absolute URL for the public shopping share page.
- Return structured JSON containing:
  - `url`
  - `expires_at`
- Log a measurement event in the audit table using action `shopping_share_clicked`.

Recommended payload details for the audit log:

- timestamp from the existing audit table
- actor value indicating app UI origin, such as `hub-ui`
- action `shopping_share_clicked`
- payload JSON including:
  - active item count at time of generation
  - expiration timestamp
  - scope marker such as `shopping`
  - mode marker such as `live_read_only`

This endpoint should not persist a snapshot of shopping items.

### 3. Public Share Route

Add a new route:

- `GET /share/shopping/<token>`

Responsibilities:

- Verify the token signature and expiry.
- Reject invalid or expired tokens cleanly.
- Load the current shopping list from the existing shopping service.
- Filter to active items only.
- Render a mobile-friendly, read-only shopping page.
- Log a measurement event in the audit table using action `shopping_share_opened`.

Recommended behavior for invalid states:

- Invalid token: render a simple invalid-link page or return a clean 404-style response.
- Expired token: render a simple expired-link page or return a clean 410-style response.

The route must not allow mutation of shopping items. It is a read-only consumer view.

### 4. Token/Auth Approach

Implement signed share tokens in `hub/utils/auth.py`.

Use the existing JWT pattern already present in the repo as the basis for the feature rather than adding a separate token technology. The shopping share feature should introduce generic helpers or a closely related helper that supports a distinct audience and claims shape for share links.

Required characteristics:

- JWT-based signed token
- separate audience for shopping sharing, for example `shopping_share`
- expiration claim
- issuer consistent with the app's existing auth helper conventions
- claim payload limited to what is necessary for verification and read scope

Recommended claims:

- `sub`
- `iss`
- `aud`
- `iat`
- `exp`
- `scope` set to `shopping`
- `view` set to `active_only`

Do not embed a shopping snapshot in the token. The token is only an authorization artifact for accessing the live read-only view.

### 5. Shopping Data Access

Reuse the existing shopping service rather than introducing a parallel data layer.

Expected data flow:

1. Shared page route verifies token.
2. Route calls existing shopping service to load current items.
3. Route filters the list to items where `done` is false.
4. Route renders a dedicated read-only template optimized for phones.

The page should not expose edit controls, delete controls, or toggle actions.

### 6. Template Changes

Create one new mobile-friendly template for the public share view.

Requirements:

- clear title such as "Shopping List"
- simple read-only active-item list
- phone-friendly spacing and typography
- optional generated/expiry metadata if useful
- empty-state message when no active items remain

Also update the existing shopping modal template to include the new share action and success state.

### 7. Audit-Based Measurement Hooks

Use the existing `audit` table as the measurement hook for this feature.

Two concrete events:

- `shopping_share_clicked`
- `shopping_share_opened`

These are the core metrics for the first iteration:

- share generation count
- share open count

From these two events, the app can later derive a simple open-through rate without adding a separate analytics platform.

## Measurement

### Event 1: `shopping_share_clicked`

Fire when the user successfully generates a share link from the shopping modal.

Suggested payload:

```json
{
  "scope": "shopping",
  "mode": "live_read_only",
  "active_item_count": 7,
  "expires_at": "2026-03-09T20:00:00Z"
}
```

### Event 2: `shopping_share_opened`

Fire when the public shared page is successfully opened with a valid token.

Suggested payload:

```json
{
  "scope": "shopping",
  "mode": "live_read_only",
  "active_item_count": 6
}
```

Primary metrics for evaluation:

- number of share links generated
- number of shared-page opens

Secondary interpretation:

- whether shopping sharing is used often enough to justify later improvements such as QR code generation, revocation, or optional snapshot links

## Test Plan

### Route and Token Tests

- Verify `POST /api/shopping/share-link` returns `200` with `url` and `expires_at`.
- Verify the returned token can be validated using the shopping-share audience.
- Verify expired tokens are rejected.
- Verify tampered tokens are rejected.
- Verify missing or malformed tokens are rejected.

### Shared Page Tests

- Verify `GET /share/shopping/<token>` renders successfully with a valid token.
- Verify only active shopping items are shown.
- Verify completed items are hidden.
- Verify an empty state is shown when all items are completed.
- Verify the page contains no edit, delete, or toggle affordances.

### Audit Logging Tests

- Verify generating a share link writes `shopping_share_clicked` to `audit`.
- Verify opening a valid shared link writes `shopping_share_opened` to `audit`.
- Verify invalid or expired tokens do not produce false-positive open events.

### UI Verification

- Open the shopping modal and confirm the `Share List` action is visible.
- Generate a link and confirm a success state appears.
- Confirm clipboard copy works when available.
- Confirm the fallback manual-copy state works if clipboard APIs are unavailable.

## Acceptance Criteria

- A user can generate a share link from the existing shopping modal.
- The generated link opens a mobile-friendly public page.
- The public page is read-only.
- The public page shows only active shopping items.
- The shared page reflects the current list state when reloaded before expiry.
- The link expires automatically.
- The token is signed and cannot be trivially forged.
- The feature adds no new database tables and no new analytics framework.
- Audit rows are written for `shopping_share_clicked` and `shopping_share_opened`.
- The implementation remains consistent with existing Family Hub routing, auth, and UI patterns.
