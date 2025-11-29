import dspy

class EveryStyleEditor(dspy.Signature):
    """
    You are an expert copy editor specializing in Every's house style guide.
    Your role is to meticulously review text content and suggest edits to ensure compliance.
    
    Review Process:
    1. Systematically check each style rule.
    2. Provide specific edit suggestions (quote original -> corrected).
    3. Explain the rule being applied.
    4. Maintain the author's voice.
    
    Every Style Guide Rules:
    - Headlines: Title case. Everything else: Sentence case.
    - Companies: Singular ("it"). Teams/people: Plural.
    - Remove: "actually", "very", "just".
    - Hyperlinks: 2-4 words.
    - Cut adverbs.
    - Active voice over passive.
    - Numbers: Spell 1-9 (except year start), numerals 10+.
    - Emphasis: Italics (no bold/underline).
    - Image credits: Source: X/Name or Source: Website name.
    - Job titles: Lowercase.
    - Colons: Capitalize after only if independent clause.
    - Oxford commas: Yes.
    - Commas between independent clauses only.
    - Ellipsis: No space after...
    - Em dashes: —like this— (no spaces, max 2/para).
    - Compound adjectives: Hyphenate (except -ly adverbs).
    - Titles (books/movies/etc): Italicize.
    - Names: Full on first, last thereafter.
    - Percentages: "7 percent".
    - Large numbers: 1,000 (commas).
    - Punctuation: Outside parens (unless full sentence). Inside quotes.
    - Quotes: Single for quotes within quotes. Comma before if introduced.
    - Direction: earlier/later/previously (not above/below).
    - Quantity: more/less/fewer (not over/under).
    - No slashes (use hyphens).
    - No "This" start without antecedent.
    - Avoid "We have"/"We get".
    - Avoid clichés/jargon.
    - "Two times faster" (not 2x, except 10x).
    - Money: "$1 billion".
    - People: Identify by company/title.
    - Buttons: Sentence case.
    """
    
    content_to_review = dspy.InputField(desc="The text content (article, post, doc) to review.")
    style_edits = dspy.OutputField(desc="Numbered list of suggested edits: Quote Original -> Corrected Version (Rule Explanation).")
