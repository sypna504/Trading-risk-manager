# Geopolitical Leakage Audit

PASS on synthetic regression tests:
- `known_at` boundary enforced;
- statement content unavailable before `statement_published_at`;
- scheduled events become features only after they were known;
- event-study windows use the declared event time without rewriting history.
