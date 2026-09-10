from fastmcp import FastMCP
from rag.vector_store import ThreatVectorStore
from typing import Dict, Any

mcp = FastMCP("compliance-server")


@mcp.tool()
async def compliance_map(finding: str) -> Dict[str, Any]:
    """Map a finding to specific controls in NIST AI RMF / ISO 27001."""
    store = ThreatVectorStore()
    results = await store.query(finding, collection="compliance_frameworks", top_k=5)

    mapped_controls = []
    for chunk in results["chunks"]:
        mapped_controls.append({
            "framework": chunk["metadata"].get("framework", "unknown"),
            "control_id": chunk["metadata"].get("control_id", "unknown"),
            "description": chunk["metadata"].get("description", ""),
            "relevance_score": chunk["score"]
        })

    return {
        "source": "Compliance Frameworks",
        "total_mappings": len(mapped_controls),
        "controls": mapped_controls
    }


if __name__ == "__main__":
    mcp.run()
