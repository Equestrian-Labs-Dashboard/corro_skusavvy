# Month filter fix — Corro / Cavali

- Corro / SKUSavvy month range starts at 2026-01. No 2025 options are shown.
- Corro `2026 YTD / current inventory` uses the current SKUSavvy stock snapshot and 2026 sales activity for rotation/turnover calculations.
- Cavali / Shopify month range starts at 2026-08.
- Cavali monthly inventory uses the latest saved Shopify inventory snapshot inside the selected month; the current snapshot is not reused for a different historical month.
- Switching between a Corro warehouse and a Cavali warehouse rebuilds the Month selector for that data source.
- Corro monthly rotation/coverage/slow-mover calculations use Shopify sales for the selected month when monthly sales data is available; stock and cost remain sourced from SKUSavvy.
