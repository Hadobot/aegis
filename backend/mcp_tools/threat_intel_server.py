from fastmcp import FastMCP
import httpx
from typing import Dict, Any

mcp = FastMCP("threat-intel-server")


@mcp.tool()
async def threat_intel_lookup(pattern: str) -> Dict[str, Any]:
    """Query NVD/CVE database for known vulnerabilities matching input patterns."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={
                    "keywordSearch": pattern,
                    "resultsPerPage": 5
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "source": "NVD",
                    "total_results": data.get("totalResults", 0),
                    "vulnerabilities": [
                        {
                            "cve_id": v["cve"]["id"],
                            "description": v["cve"]["descriptions"][0]["value"][:200],
                            "severity": v.get("metrics", {}).get(
                                "cvssMetricV31", [{}]
                            )[0].get("cvssData", {}).get("baseSeverity", "UNKNOWN")
                        }
                        for v in data.get("vulnerabilities", [])[:5]
                    ]
                }
            return {"source": "NVD", "error": "API returned non-200 status"}
        except Exception as e:
            return {"source": "NVD", "error": str(e)}


if __name__ == "__main__":
    mcp.run()
