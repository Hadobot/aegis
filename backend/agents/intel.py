import httpx
from typing import Dict, Any


class IntelAgent:
    """
    INTEL - Fetches latest threat intelligence.
    Provides real-time context to Sentry and Shield.
    """

    def __init__(self):
        self.agent_id = "intel"

    async def enrich_threat(self, threat_type: str, pattern: str) -> Dict[str, Any]:
        enrichment = {
            "agent_id": self.agent_id,
            "threat_type": threat_type,
            "original_pattern": pattern,
            "intelligence": {}
        }

        # Fetch CVE data
        cve_data = await self._fetch_cve(pattern)
        enrichment["intelligence"]["cve"] = cve_data

        # Fetch OWASP context
        owasp_data = await self._fetch_owasp_context(threat_type)
        enrichment["intelligence"]["owasp"] = owasp_data

        # Fetch MITRE techniques
        mitre_data = await self._fetch_mitre_techniques(threat_type)
        enrichment["intelligence"]["mitre"] = mitre_data

        return enrichment

    async def _fetch_cve(self, pattern: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://services.nvd.nist.gov/rest/json/cves/2.0",
                    params={"keywordSearch": pattern, "resultsPerPage": 3},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
            except Exception:
                pass
        return {"error": "Could not fetch CVE data"}

    async def _fetch_owasp_context(self, threat_type: str) -> Dict[str, Any]:
        owasp_map = {
            "prompt_injection": "OWASP-LLM01",
            "jailbreak": "OWASP-LLM01",
            "data_exfiltration": "OWASP-LLM02",
            "role_hijacking": "OWASP-LLM01",
            "encoding_bypass": "OWASP-LLM01",
            "multi_turn": "OWASP-LLM01"
        }

        return {
            "primary_reference": owasp_map.get(threat_type, "unknown"),
            "framework": "OWASP LLM Top 10 2025"
        }

    async def _fetch_mitre_techniques(self, threat_type: str) -> Dict[str, Any]:
        mitre_map = {
            "prompt_injection": "AML.T0051",
            "jailbreak": "AML.T0051",
            "data_exfiltration": "AML.T0053",
            "role_hijacking": "AML.T0051"
        }

        return {
            "technique_id": mitre_map.get(threat_type, "unknown"),
            "framework": "MITRE ATLAS"
        }
