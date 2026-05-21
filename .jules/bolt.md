## 2024-05-21 - [Optimized Token Counter Encoding with lru_cache and LRUCache]
**Learning:**
1. Using `functools.lru_cache` dynamically to hold large raw strings can cause severe memory leaks, as the decorator retains strong references to all function arguments.
2. The dynamic retrieval of `tiktoken.encoding_for_model` inside loop functions constitutes a massive computational bottleneck, which can be elegantly resolved via a simple `@functools.lru_cache(maxsize=128)` helper without referencing the raw text.
3. Moving to `cachetools.LRUCache` to hold MD5 hashed keys maintains memory constraints while automatically handling size-based eviction.
**Action:** Use `functools.lru_cache` exclusively for static or lightweight lookups (like model encodings), and utilize explicit MD5 string hashing mapping to an explicit `cachetools.LRUCache` instance to limit RAM bloat for large string caches.
