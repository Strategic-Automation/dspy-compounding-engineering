from agents.review.schema import ReviewReport
from pydantic import Field
import dspy


class SecurityReport(ReviewReport):
    risk_matrix: str = Field(..., description="Summary of findings by severity")


class SecuritySentinel(dspy.Signature):
    """
    You are an elite Application Security Specialist with deep expertise in identifying and mitigating security vulnerabilities.

    ## Core Security Scanning Protocol
    1. Input Validation Analysis (sanitization, types, limits).
    2. SQL Injection Risk Assessment (parameterization, concatenation).
    3. XSS Vulnerability Detection (escaping, CSP).
    4. Authentication & Authorization Audit (endpoints, sessions, RBAC).
    5. Sensitive Data Exposure (secrets, logs, encryption).
    6. OWASP Top 10 Compliance.
    """

    code_diff: str = dspy.InputField(desc="The code changes to review")
    security_report: SecurityReport = dspy.OutputField(
        desc="Structured security audit report"
    )
