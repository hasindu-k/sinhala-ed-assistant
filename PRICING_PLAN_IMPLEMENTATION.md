# Pricing Plan Implementation Tracker

This document tracks the implementation of Basic, Intermediate, and Enterprise pricing tiers for the Sinhala Educational Assistant.

## Current Status

- Status: Phase 2 complete
- Owner: TBD
- Started: 2026-04-30
- Main user field: `users.tier`
- Proposed permission field: `users.role`
- Current default tier in code: `basic`
- Target default tier: `basic`

## Target Plans

| Tier | Price | Badge | Learning Limit | Evaluation Session Limit | Per-Session Evaluation Limit |
| --- | --- | --- | --- | --- | --- |
| `basic` | Free forever | Starter | 5 requests/hour | 1 session/day | 10 evaluations/session |
| `intermediate` | 5000 LKR/tier | Most Popular | 20 requests/hour | 5 sessions/day | TBD |
| `enterprise` | 10000 LKR onwards/tier | Best for Scale | 50 requests/hour | 10 sessions/day | Extra evaluations billable |

## Decisions To Confirm

- [ ] Should evaluation daily limits reset by calendar day in `Asia/Colombo`, or by rolling 24-hour window?
- [ ] For Intermediate, is there a per-session evaluation limit, or only 5 sessions/day?
- [ ] For Enterprise, should extra evaluations be allowed automatically, or blocked until billing/admin approval?
- [ ] Should users be able to upgrade tier directly, or only admins/payment webhook should update `users.tier`?
- [ ] Should old tiers be mapped as `normal -> basic`, `classroom -> intermediate`, `institution -> enterprise`?
- [ ] Should the first admin user be created by migration, seed script, or manual database update?
- [ ] Should plan limits remain code-managed for now, or should admins be able to edit plan limits from the database?

## Tier Vs Role

Keep subscription tier and authorization role separate.

| Field | Purpose | Example Values |
| --- | --- | --- |
| `users.tier` | Controls usage limits and pricing plan | `basic`, `intermediate`, `enterprise` |
| `users.role` | Controls permissions and admin access | `user`, `admin` |

An Enterprise user should not automatically become an admin. An admin can manage users, tiers, and future pricing settings without needing an Enterprise subscription.

## Implementation Checklist

### Phase 1: Plan Configuration

- [x] Create a single source of truth for pricing plans, for example `app/core/pricing_plans.py`.
- [x] Define internal tier keys: `basic`, `intermediate`, `enterprise`.
- [x] Include marketing metadata needed by frontend: name, description, badge, price, CTA, note, features.
- [x] Include enforceable limits: learning requests/hour, evaluation sessions/day, evaluations/session, overage behavior.

### Phase 2: User Tier Model And Migration

- [x] Update `app/shared/models/user.py` so `tier` defaults to `basic`.
- [x] Create Alembic migration to change database default to `basic`.
- [x] Migrate existing rows:
  - [x] `normal` -> `basic`
  - [x] `classroom` -> `intermediate`
  - [x] `institution` -> `enterprise`
- [x] Expose `tier` in `app/schemas/user.py` response models if frontend needs it.

### Phase 3: Admin Role And Permissions

- [ ] Add `role` column to `app/shared/models/user.py`.
- [ ] Use default role `user`.
- [ ] Create Alembic migration for `users.role`.
- [ ] Decide how the first admin account is created.
- [ ] Expose `role` in user response only if needed by frontend.
- [ ] Add helper/dependency such as `require_admin_user`.
- [ ] Protect tier-management endpoints with admin-only access.
- [ ] Protect future plan-management endpoints with admin-only access.

### Phase 4: Usage Service

- [ ] Refactor `app/services/usage_service.py` to use the new plan config.
- [ ] Add `check_learning_request_limit(user_id)`.
- [ ] Add `check_evaluation_session_limit(user_id)`.
- [ ] Add `check_evaluations_per_session_limit(user_id, answer_resource_ids)`.
- [ ] Return clear HTTP 403 errors with current tier and limit details.
- [ ] Decide whether unknown tier should fallback to `basic` or fail loudly.

### Phase 5: Learning Mode Enforcement

- [ ] Add learning limit check to `app/routers/messages.py` before user message creation.
- [ ] Add learning limit check to voice learning endpoints in `app/components/voice_qa/routers/voice_router.py`.
- [ ] Make sure only user-created learning requests count, not assistant/system messages.
- [ ] Make sure evaluation-mode chat messages do not consume learning quota unless intentionally required.

### Phase 6: Evaluation Mode Enforcement

- [ ] Replace current evaluation limit check in `app/services/evaluation/evaluation_workflow_service.py`.
- [ ] Enforce daily evaluation session limit before creating or starting a new evaluation session.
- [ ] Enforce Basic per-session evaluation limit of 10 answer scripts.
- [ ] Implement Enterprise overage behavior.
- [ ] Avoid double-counting reused evaluation sessions if `process_documents` created a session earlier.

### Phase 7: API Endpoints

- [ ] Add `GET /api/v1/pricing/plans`.
- [ ] Add `GET /api/v1/usage/me`.
- [ ] Add admin-only tier update flow.
- [ ] Optionally add payment-webhook tier update flow later.
- [ ] Register new router in `app/api/v1/router.py`.

### Phase 8: Future Admin-Managed Plan Limits

- [ ] Add database table for editable pricing plans if runtime updates are needed.
- [ ] Add admin-only CRUD endpoints for pricing plans.
- [ ] Track who updated plan limits with `updated_by`.
- [ ] Track when plan limits changed with `updated_at`.
- [ ] Keep audit history if pricing changes affect billing or contractual limits.

Possible future table:

| Column | Purpose |
| --- | --- |
| `tier_key` | Stable tier identifier |
| `name` | Display name |
| `price_lkr` | Fixed LKR price, if applicable |
| `price_lkr_from` | Starting price for Enterprise |
| `learning_requests_per_hour` | Learning quota |
| `evaluation_sessions_per_day` | Daily session quota |
| `evaluations_per_session` | Per-session answer/evaluation quota |
| `allow_overage` | Whether extra usage can continue |
| `is_active` | Whether the plan is available |
| `updated_by` | Admin user who last changed the plan |
| `updated_at` | Last update timestamp |

### Phase 9: Tests

- [ ] Test Basic learning limit: 5 requests/hour allowed, 6th blocked.
- [ ] Test Intermediate learning limit: 20 requests/hour.
- [ ] Test Enterprise learning limit: 50 requests/hour.
- [ ] Test Basic evaluation sessions: 1/day allowed, 2nd blocked.
- [ ] Test Intermediate evaluation sessions: 5/day.
- [ ] Test Enterprise evaluation sessions: 10/day.
- [ ] Test Basic evaluations/session: 10 allowed, 11th blocked.
- [ ] Test migration maps old tiers correctly.
- [ ] Test pricing plans endpoint returns all required frontend metadata.
- [ ] Test normal users cannot update tiers.
- [ ] Test admins can update user tiers.
- [ ] Test admin-only endpoints reject unauthenticated users.
- [ ] Test admin-only endpoints reject authenticated non-admin users.

## Code Touchpoints

- `app/shared/models/user.py`
- `app/schemas/user.py`
- `app/core/security.py`
- `app/core/pricing_plans.py`
- `app/services/usage_service.py`
- `app/routers/messages.py`
- `app/components/voice_qa/routers/voice_router.py`
- `app/services/evaluation/evaluation_workflow_service.py`
- `app/api/v1/router.py`
- `app/core/config.py`
- `migrations/versions/`
- `tests/`

## Notes

- Learning requests reset every hour.
- Evaluation limits reset daily.
- Enterprise customers may be billed for extra evaluations after exceeding the included quota.
- The current `UsageService` uses old tier names and a 12-hour evaluation window, so it should be refactored rather than extended as-is.
