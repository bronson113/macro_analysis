# Remove Evidence Assessments from the Dashboard

## Problem

The dashboard's Evidence Assessments section is non-discriminating. Every sector currently uses the same seven equally weighted factor slots, valuation is missing for every sector, and each card therefore reports 85.7% coverage (shown as 86%). The missing factor also expands every score range to `-10` through `+10` and leaves every posture `NEUTRAL`. Presenting these repeated values implies useful differentiation that the underlying model does not provide.

## Decision

Remove the Evidence Assessments feature from the React dashboard. Remove its navigation entry, rendered section, component, presentation utility and test, and feature-specific CSS. Renumbering remains automatic because navigation numbers are derived from the remaining ordered section list.

Keep backend evidence generation, payload export, reports, signal storage, and evaluation code unchanged. Those records may still support offline research and historical continuity, and removing them would broaden this UI correction into a data migration.

## Data Flow

`data.json` may continue to contain `evidence_assessments`, but `App.jsx` will no longer read or render that field. The dashboard will render Editorial Review, Daily Brief, Trends, Indicators, Deep Dive, and Source Health in that order.

## Testing

Update the dashboard-section ordering test first so it expects no Evidence entry, then verify that it fails against the current implementation. Remove the dashboard feature and its now-unused files/styles, rerun the complete web test suite, run the linter, and build the production bundle. A repository search must find no remaining Evidence Assessment UI imports, component references, navigation entries, feature-specific CSS selectors, or presentation utility references under `web/src`.

## Scope Boundaries

- Do not change evidence calculations or claim that the repeated 86% has been corrected.
- Do not remove `evidence_assessments` from generated payloads, reports, storage, or evaluation pipelines.
- Do not alter unrelated dashboard sections or styling.
