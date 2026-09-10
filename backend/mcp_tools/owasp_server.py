from fastmcp import FastMCP
from typing import Dict, Any, List

mcp = FastMCP("owasp-server")

OWASP_LLM_TOP_10 = [
    {
        "id": "OWASP-LLM01",
        "name": "Prompt Injection",
        "description": "Attackers craft inputs that override system instructions",
        "severity": "critical",
        "mitigations": [
            "Input validation and sanitization",
            "Permission controls",
            "Prompt hardening with system instructions"
        ]
    },
    {
        "id": "OWASP-LLM02",
        "name": "Sensitive Data Disclosure",
        "description": "LLM reveals sensitive information in responses",
        "severity": "high",
        "mitigations": [
            "Data classification and handling",
            "Output filtering",
            "Access controls"
        ]
    },
    {
        "id": "OWASP-LLM03",
        "name": "Supply Chain Vulnerabilities",
        "description": "Vulnerabilities in LLM dependencies and training data",
        "severity": "high",
        "mitigations": [
            "Dependency scanning",
            "Model provenance verification",
            "Training data auditing"
        ]
    },
    {
        "id": "OWASP-LLM04",
        "name": "Data and Model Poisoning",
        "description": "Manipulation of training data or fine-tuning",
        "severity": "high",
        "mitigations": [
            "Data validation",
            "Training pipeline security",
            "Model versioning"
        ]
    },
    {
        "id": "OWASP-LLM05",
        "name": "Improper Output Handling",
        "description": "LLM outputs not properly validated before execution",
        "severity": "medium",
        "mitigations": [
            "Output validation",
            "Sandboxing",
            "Content Security Policy"
        ]
    },
    {
        "id": "OWASP-LLM06",
        "name": "Excessive Agency",
        "description": "LLM given too many permissions or capabilities",
        "severity": "high",
        "mitigations": [
            "Principle of least privilege",
            "Permission scoping",
            "Human-in-the-loop"
        ]
    },
    {
        "id": "OWASP-LLM07",
        "name": "System Prompt Leakage",
        "description": "Attackers extract system prompt contents",
        "severity": "medium",
        "mitigations": [
            "Prompt isolation",
            "Output filtering",
            "Separate sensitive logic"
        ]
    },
    {
        "id": "OWASP-LLM08",
        "name": "Vector and Embedding Weaknesses",
        "description": "Vulnerabilities in RAG implementations",
        "severity": "medium",
        "mitigations": [
            "Embedding validation",
            "Source verification",
            "Access controls on vector stores"
        ]
    },
    {
        "id": "OWASP-LLM09",
        "name": "Misinformation",
        "description": "LLM generates false or misleading information",
        "severity": "medium",
        "mitigations": [
            "Fact-checking",
            "Source attribution",
            "Confidence scoring"
        ]
    },
    {
        "id": "OWASP-LLM10",
        "name": "Unbounded Consumption",
        "description": "Excessive resource usage leading to denial of service",
        "severity": "low",
        "mitigations": [
            "Rate limiting",
            "Resource quotas",
            "Cost monitoring"
        ]
    }
]


@mcp.tool()
async def owasp_llm_query(threat_description: str) -> Dict[str, Any]:
    """Search OWASP LLM Top 10 for matching attack classifications."""
    threat_lower = threat_description.lower()

    matches = []
    for item in OWASP_LLM_TOP_10:
        score = 0
        if any(word in item["name"].lower() for word in threat_lower.split()):
            score += 2
        if any(word in item["description"].lower() for word in threat_lower.split()):
            score += 1

        if score > 0:
            matches.append({**item, "match_score": score})

    matches.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "source": "OWASP LLM Top 10",
        "total_matches": len(matches),
        "matches": matches[:5]
    }


if __name__ == "__main__":
    mcp.run()
