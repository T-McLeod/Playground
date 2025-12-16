import os
from app.interfaces.rag_interface import RAGInterface


def get_rag_service() -> RAGInterface:
    """Return an instance of the configured RAG service.

    Behavior:
    - Reads `RAG_PROVIDER` from the environment (defaults to 'vertex').

    Any `kwargs` are forwarded to the provider class constructor.
    """
    provider = (os.environ.get("RAG_PROVIDER") or "vertex").strip().lower()

    if provider == "vertex":
        from app.services.rag_services.vertex_service.vertex_service import VertexRAGService
        return VertexRAGService()
    else:
        raise ValueError(
            f"RAG provider '{provider}' is not supported. Set environment variable RAG_PROVIDER to available providers."
        )
