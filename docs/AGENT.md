# Analytical agent

The agent is read-only. Allowed tools cover market/model/decision/news/event/outcome/research/paper/system records. Forbidden actions include order execution, portfolio mutation, model promotion/rollback, threshold/risk changes and source-credibility changes. `POST /api/v1/agent/query` returns answer, evidence, uncertainty and model/fallback status.
