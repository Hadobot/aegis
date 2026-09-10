from fastmcp import FastMCP
from typing import Dict, Any

mcp = FastMCP("mitre-server")

MITRE_ATLAS_TECHNIQUES = [
    {
        "id": "AML.T0051",
        "name": "LLM Prompt Injection",
        "tactic": "Initial Access",
        "description": "Adversary manipulates LLM via crafted prompts"
    },
    {
        "id": "AML.T0052",
        "name": "LLM Supply Chain Attack",
        "tactic": "Supply Chain Compromise",
        "description": "Adversary compromises model or training data"
    },
    {
        "id": "AML.T0053",
        "name": "ML Model Exfiltration",
        "tactic": "Exfiltration",
        "description": "Adversary steals model weights or architecture"
    },
    {
        "id": "AML.T0054",
        "name": "ML Attack Stage",
        "tactic": "Execution",
        "description": "Adversary executes attack against ML system"
    }
]


@mcp.tool()
async def mitre_atlas_search(threat_pattern: str) -> Dict[str, Any]:
    """Find MITRE ATLAS techniques matching detected threat patterns."""
    pattern_lower = threat_pattern.lower()

    matches = []
    for technique in MITRE_ATLAS_TECHNIQUES:
        if any(word in technique["name"].lower() for word in pattern_lower.split()):
            matches.append(technique)

    return {
        "source": "MITRE ATLAS",
        "total_matches": len(matches),
        "techniques": matches
    }


if __name__ == "__main__":
    mcp.run()
