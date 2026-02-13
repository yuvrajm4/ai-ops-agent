from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from tools.common_functions import get_embeddings


class IncidentVectorStore:
    def __init__(self):
        self.embeddings = get_embeddings()
        self.store = None

    def add_incident(
        self,
        incident_id: str,
        description: str,
        incident_type: str,
        root_cause: str
    ):
        text = f"""
        Incident description: {description}
        Incident type: {incident_type}
        Root cause: {root_cause}
        """

        doc = Document(
            page_content=text,
            metadata={
                "incident_id": incident_id,
                "incident_type": incident_type
            }
        )

        if self.store is None:
            self.store = FAISS.from_documents([doc], self.embeddings)
        else:
            self.store.add_documents([doc])

    def search_similar(self, query: str, k: int = 3):
        if not self.store:
            return []
        return self.store.similarity_search(query, k=k)
