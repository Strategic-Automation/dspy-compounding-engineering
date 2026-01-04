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

    **Goal:** Create a comprehensive, well-structured implementation plan.
    """

    feature_description = dspy.InputField(desc="The feature description")
    research_summary = dspy.InputField(desc="Combined research findings")
    spec_flow_analysis = dspy.InputField(desc="SpecFlow analysis results")
    plan_report: PlanReport = dspy.OutputField(desc="The structured implementation plan")
