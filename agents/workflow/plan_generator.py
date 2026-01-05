import dspy

from agents.schema import PlanReport


class PlanGenerator(dspy.Signature):
    """
    Transform feature descriptions and research findings into a structured
    implementation plan.

    **STRICT OUTPUT PROTOCOL:**
    1. Provide ONLY the requested fields for the PlanReport.
    2. Use `[[ ## plan_report ## ]]` followed by the structured report.
    3. Do NOT include any notes, hints, or instructions (e.g., "# note: ...") in your output.
    4. Keep the tone professional, technical, and concise.
    5. No emojis or decorative formatting.

    **SCOPE CONSTRAINTS:**
    6. Match the scope of changes to the severity of the finding:
       - P1 CRITICAL: Focused fix only, minimal changes to solve the immediate problem
       - P2 IMPORTANT: Moderate changes, stay within affected files and their tests
       - P3 NICE-TO-HAVE: Can propose broader improvements if warranted
    7. Prefer MINIMAL changes that solve the problem over comprehensive rewrites.
    8. Do NOT propose new files, schemas, or configurations unless explicitly requested.
    9. Implementation steps should be actionable by a single developer in < 2 hours.
    10. If research suggests multiple approaches, pick the simplest one that meets the need.

    **Goal:** Create a focused, actionable implementation plan with minimal scope.
    """

    feature_description = dspy.InputField(desc="The feature description")
    research_summary = dspy.InputField(desc="Combined research findings")
    spec_flow_analysis = dspy.InputField(desc="SpecFlow analysis results")
    plan_report: PlanReport = dspy.OutputField(desc="The structured implementation plan")

