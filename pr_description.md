⚡ Optimize local search tag filtering

💡 **What:** Added a dynamic SQLite `LIKE` clause to the `search_local` method to pre-filter rows when `tags` are provided. The exact same Python manual tag filtering is retained to discard false positives.
🎯 **Why:** The previous implementation fetched all rows and iterated over them in Python, parsing JSON for each to check tags. This was highly inefficient. By using SQLite string matching as a pre-filter, we vastly reduce the number of rows processed in Python while guaranteeing backward compatibility with older SQLite versions (avoiding `JSON_EXTRACT` dependency).
📊 **Measured Improvement:** In a local benchmark script querying over 50,000 mock rows:
* **Before (Baseline):** ~0.145 seconds
* **After (Optimized):** ~0.027 seconds (an ~80% improvement).
