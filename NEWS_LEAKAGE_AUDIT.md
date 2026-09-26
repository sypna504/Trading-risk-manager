# NEWS LEAKAGE AUDIT — MVP-6

## Decision-time contract

For a news row to contribute to features at prediction time `t`, all of these must hold:

```text
published_at <= t
received_at  <= t
research_known_at <= t
```

`research_known_at` is the maximum of the timestamps available in the row:

```text
published_at
received_at
known_at      (when supplied)
edited_at     (when supplied)
```

This makes late arrival and later edits conservative: the current stored article body is never backfilled to a time before the latest known/edit timestamp.

## Important storage limitation

The current `news_items` table stores the latest edit of an article rather than an immutable version history. Because the old text cannot be reconstructed, MVP-6 takes the conservative route and makes an edited row unavailable before `edited_at`. A future research-grade historical news store should persist content versions with their own `known_at`.

## Scheduled events

`schedule_macro_event_nearby` is allowed only when the calendar/news row itself is already known. The scheduled event time may be in the future; statement/result content is not available until its publication/known time.

## Deduplication

Event counts are based on a stable event key (`duplicate_group_id`, then source/external id, then id). Independent-source count is kept separately, so two sources confirming one event do not inflate event count but can increase source diversity.

## Regression coverage

- future news excluded;
- late article excluded until receive time;
- future edit excluded until edit time;
- explicit `known_at` enforced;
- duplicate event count not inflated;
- exact timestamp boundary included;
- no-news and missing-news paths are neutral;
- asset relevance filter checked;
- price-only result reproducible under different news;
- news-only result reproducible;
- chronological final holdout boundary checked;
- synthetic evidence cannot authorize a production gate change.

Result: **PASS**.
