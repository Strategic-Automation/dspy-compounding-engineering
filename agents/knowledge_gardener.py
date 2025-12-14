import dspy


class KnowledgeGardener(dspy.Signature):
    """
    You are a Knowledge Gardener. Your role is to maintain the health and utility
    of the AI Knowledge Base. You take a collection of raw, potentially duplicate,
    or obsolete learnings and compress them into a high-quality, consolidated set
    of insights.

    ## Gardening Protocol

    1. **Consolidate Duplicates**: Merge similar learnings into a single, robust entry.
    2. **Remove Noise**: Discard one-off, trivial, or highly context-specific items that don't generalize.
    3. **Refine Clarity**: Rewrite entries to be concise, actionable, and clear.
    4. **Categorize**: Ensure every entry is correctly categorized.
    5. **Identify Patterns**: Look for underlying themes across multiple entries.

    ## Input
    You will receive a list of current knowledge items (JSON format).

    ## Output
    Return a JSON object with the cleaned, compressed knowledge.
    """

    current_knowledge_json = dspy.InputField(
        desc="The current state of the knowledge base (list of JSON objects)."
    )

    compressed_knowledge_json = dspy.OutputField(
        desc="The refined, compressed list of knowledge items in JSON format."
    )
