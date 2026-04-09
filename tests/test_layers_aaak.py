from mempalace import layers


class _FakeCollection:
    def __init__(self, docs, metas):
        self._docs = docs
        self._metas = metas

    def get(self, include=None, limit=500, offset=0, where=None):
        if offset > 0:
            return {"documents": [], "metadatas": []}
        return {"documents": self._docs, "metadatas": self._metas}

    def query(self, query_texts, n_results, include, where=None):
        docs = self._docs[:n_results]
        metas = self._metas[:n_results]
        dists = [0.1 for _ in docs]
        return {"documents": [docs], "metadatas": [metas], "distances": [dists]}


class _FakeClient:
    docs = []
    metas = []

    def __init__(self, path):
        self.path = path

    def get_collection(self, name):
        assert name == "mempalace_drawers"
        return _FakeCollection(self.docs, self.metas)


class _FakeDialect:
    def compress(self, text, metadata=None):
        return f"AAAK<{text[:12]}>"


def _sample_docs_and_metas():
    docs = [
        "Newest memory should stay raw.",
        "Second newest memory should stay raw.",
        "Third newest memory should stay raw.",
        "Older memory should be compressed.",
    ]
    metas = [
        {"wing": "project", "room": "alpha", "source_file": "a.txt", "filed_at": "2026-04-08T12:00:00"},
        {"wing": "project", "room": "alpha", "source_file": "b.txt", "filed_at": "2026-04-07T12:00:00"},
        {"wing": "project", "room": "alpha", "source_file": "c.txt", "filed_at": "2026-04-06T12:00:00"},
        {"wing": "project", "room": "alpha", "source_file": "d.txt", "filed_at": "2026-03-01T12:00:00"},
    ]
    return docs, metas


def test_layer1_compresses_only_older_context(monkeypatch):
    docs, metas = _sample_docs_and_metas()
    _FakeClient.docs = docs
    _FakeClient.metas = metas

    monkeypatch.setattr(layers.chromadb, "PersistentClient", _FakeClient)
    monkeypatch.setattr(layers, "Dialect", _FakeDialect)

    l1 = layers.Layer1(palace_path="/tmp/palace", aaak_older_context=True)
    rendered = l1.generate()

    assert "Newest memory should stay raw." in rendered
    assert "Second newest memory should stay raw." in rendered
    assert "Third newest memory should stay raw." in rendered
    assert "AAAK<Older memory" in rendered


def test_layer2_retrieval_is_aaak_compressed(monkeypatch):
    docs, metas = _sample_docs_and_metas()
    _FakeClient.docs = docs
    _FakeClient.metas = metas

    monkeypatch.setattr(layers.chromadb, "PersistentClient", _FakeClient)
    monkeypatch.setattr(layers, "Dialect", _FakeDialect)

    l2 = layers.Layer2(palace_path="/tmp/palace", aaak_retrieval=True)
    rendered = l2.retrieve(wing="project", n_results=2)

    assert "AAAK<Newest memor>" in rendered
    assert rendered.count("AAAK<") == 2
    assert "Second newest memory should stay raw." not in rendered


def test_layer3_search_is_aaak_compressed(monkeypatch):
    docs, metas = _sample_docs_and_metas()
    _FakeClient.docs = docs
    _FakeClient.metas = metas

    monkeypatch.setattr(layers.chromadb, "PersistentClient", _FakeClient)
    monkeypatch.setattr(layers, "Dialect", _FakeDialect)

    l3 = layers.Layer3(palace_path="/tmp/palace", aaak_retrieval=True)
    rendered = l3.search("older", n_results=1)

    assert "AAAK<Newest memor>" in rendered
