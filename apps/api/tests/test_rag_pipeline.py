from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.provider import EmbeddingProvider
from app.api.dependencies import get_db
from app.db.base import Base
from app.db.models import Document, DocumentChunk, KnowledgeBase, Organization, OrganizationMember, User, Workspace
from app.main import app
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService


class StubEmbeddingProvider(EmbeddingProvider):
    def __init__(self, vectors: dict[str, list[float]] | None = None) -> None:
        super().__init__()
        self.vectors = vectors or {}

    def embed_text(self, text: str, **kwargs: object) -> list[float]:
        return self.vectors.get(text, [0.1] * 1536)

    def embed_documents(self, documents: list[str], **kwargs: object) -> list[list[float]]:
        return [self.vectors.get(document, [0.1] * 1536) for document in documents]


@pytest.fixture
def rag_session():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = SessionLocal()

    org = Organization(name='Org One', slug='org-one')
    user = User(email='user@example.com', password_hash='hash', full_name='User One')
    workspace_a = Workspace(organization_id=1, owner_id=1, name='Workspace A', slug='workspace-a')
    workspace_b = Workspace(organization_id=1, owner_id=1, name='Workspace B', slug='workspace-b')
    org_member = OrganizationMember(organization_id=1, user_id=1, role='admin', status='active')
    kb_a = KnowledgeBase(workspace_id=1, name='KB A', created_by=1)
    kb_b = KnowledgeBase(workspace_id=2, name='KB B', created_by=1)

    session.add_all([org, user, workspace_a, workspace_b, org_member, kb_a, kb_b])
    session.commit()

    document_a = Document(
        workspace_id=workspace_a.id,
        knowledge_base_id=kb_a.id,
        created_by=1,
        title='Alpha',
        file_name='alpha.txt',
        mime_type='text/plain',
        storage_path='/tmp/alpha.txt',
        status='COMPLETED',
        extracted_text='Alpha answer text',
    )
    document_b = Document(
        workspace_id=workspace_b.id,
        knowledge_base_id=kb_b.id,
        created_by=1,
        title='Beta',
        file_name='beta.txt',
        mime_type='text/plain',
        storage_path='/tmp/beta.txt',
        status='COMPLETED',
        extracted_text='Beta answer text',
    )
    session.add_all([document_a, document_b])
    session.commit()

    alpha_embedding = [1.0] + [0.0] * 1535
    beta_embedding = [0.0, 1.0] + [0.0] * 1534

    chunk_a = DocumentChunk(
        workspace_id=workspace_a.id,
        document_id=document_a.id,
        chunk_index=0,
        content='Alpha chunk for workspace A',
        embedding=alpha_embedding,
    )
    chunk_b = DocumentChunk(
        workspace_id=workspace_b.id,
        document_id=document_b.id,
        chunk_index=0,
        content='Beta chunk for workspace B',
        embedding=beta_embedding,
    )
    session.add_all([chunk_a, chunk_b])
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session, workspace_a, workspace_b, kb_a, kb_b
    app.dependency_overrides.clear()
    session.close()


def test_workspace_scoped_retrieval_filters_out_other_workspace(rag_session):
    session, workspace_a, workspace_b, kb_a, kb_b = rag_session
    provider = StubEmbeddingProvider({'Alpha question': [1.0] + [0.0] * 1535})
    service = RetrievalService(session, embedding_provider=provider, top_k=5)

    results = service.retrieve(
        workspace_id=workspace_a.id,
        query_text='Alpha question',
        knowledge_base_id=kb_a.id,
    )

    assert len(results) == 1
    assert results[0].document_id == 1
    assert results[0].workspace_id == workspace_a.id


def test_insufficient_evidence_returns_explicit_state(rag_session):
    session, workspace_a, _workspace_b, kb_a, _kb_b = rag_session
    provider = StubEmbeddingProvider({'What is the answer?': [0.1] * 1536})
    rag = RAGService(session, embedding_provider=provider)

    response = rag.query(
        user_id=1,
        workspace_id=workspace_a.id,
        knowledge_base_id=kb_a.id,
        query_text='What is the answer?',
        top_k=5,
        min_similarity=0.2,
    )

    assert response['insufficient_evidence'] is True
    assert 'couldn\'t find enough information' in response['answer'].lower()


def test_citation_metadata_maps_to_real_chunks(rag_session):
    session, workspace_a, _workspace_b, kb_a, _kb_b = rag_session
    provider = StubEmbeddingProvider({'Alpha question': [1.0] + [0.0] * 1535})
    rag = RAGService(session, embedding_provider=provider)

    response = rag.query(
        user_id=1,
        workspace_id=workspace_a.id,
        knowledge_base_id=kb_a.id,
        query_text='Alpha question',
        top_k=5,
        min_similarity=0.2,
    )

    assert response['citations'][0]['document_id'] == 1
    assert response['citations'][0]['chunk_id'] == 1
    assert response['citations'][0]['file_name'] == 'alpha.txt'


def test_embedding_provider_failures_are_surfaces(rag_session):
    class BrokenProvider(EmbeddingProvider):
        def embed_text(self, text: str, **kwargs: object) -> list[float]:
            raise RuntimeError('embedding failed')

        def embed_documents(self, documents: list[str], **kwargs: object) -> list[list[float]]:
            raise RuntimeError('embedding failed')

    session, workspace_a, _workspace_b, kb_a, _kb_b = rag_session
    rag = RAGService(session, embedding_provider=BrokenProvider())

    with pytest.raises(RuntimeError):
        rag.query(
            user_id=1,
            workspace_id=workspace_a.id,
            knowledge_base_id=kb_a.id,
            query_text='Alpha question',
            top_k=5,
            min_similarity=0.2,
        )
