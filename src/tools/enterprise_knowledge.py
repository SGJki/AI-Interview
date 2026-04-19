"""Enterprise Knowledge Base retrieval client."""
import logging
from typing import Optional

import httpx

from src.agent.state import InterviewState

logger = logging.getLogger(__name__)

# Enterprise KB API configuration
ENTERPRISE_KB_BASE_URL = "http://localhost:8080"
ENTERPRISE_KB_TIMEOUT = 10  # seconds


def get_enterprise_kb_client() -> httpx.AsyncClient:
    """Get HTTP client for enterprise KB API."""
    return httpx.AsyncClient(
        base_url=ENTERPRISE_KB_BASE_URL,
        timeout=ENTERPRISE_KB_TIMEOUT,
    )


async def retrieve_enterprise_knowledge(
    module: Optional[str] = None,
    skill_point: Optional[str] = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Retrieve enterprise knowledge documents.

    Args:
        module: Module name (priority if provided)
        skill_point: Skill point (fallback)
        top_k: Number of results to return

    Returns:
        List of document dicts with content, metadata, score
    """
    if not module and not skill_point:
        return []

    try:
        async with get_enterprise_kb_client() as client:
            # Priority: module > skill_point
            if module:
                response = await client.post(
                    "/retrieve/by-module",
                    json={"module": module, "top_k": top_k}
                )
            else:
                response = await client.post(
                    "/retrieve/by-skill",
                    json={"skill_point": skill_point, "top_k": top_k}
                )

            response.raise_for_status()
            data = response.json()

            return data.get("documents", [])

    except httpx.TimeoutException:
        logger.warning("Enterprise KB timeout, proceeding without it")
        return []
    except httpx.HTTPStatusError as e:
        logger.warning(f"Enterprise KB returned {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Enterprise KB error: {e}")
        return []


async def ensure_enterprise_docs(state: InterviewState) -> tuple[list[dict], dict]:
    """
    Ensure enterprise docs are retrieved and cached in state.

    Args:
        state: InterviewState

    Returns:
        tuple: (docs, state_updates)
        - docs: list of enterprise knowledge documents
        - state_updates: dict to merge into state (with enterprise_docs and enterprise_docs_retrieved)
    """
    if state.enterprise_docs_retrieved:
        return state.enterprise_docs, {}

    docs = await retrieve_enterprise_knowledge(
        module=state.current_module,
        skill_point=state.current_skill_point,
        top_k=3,
    )

    state_updates = {
        "enterprise_docs": docs,
        "enterprise_docs_retrieved": True,
    }

    return docs, state_updates
