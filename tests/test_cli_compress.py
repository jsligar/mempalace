from types import SimpleNamespace

import mempalace.cli as cli


class _FakeCollection:
    def __init__(self):
        self.upserts = []

    def get(self, include=None, limit=500, offset=0, where=None):
        if offset > 0:
            return {"documents": [], "metadatas": [], "ids": []}
        return {
            "documents": ["We decided to use GraphQL for the API layer."],
            "metadatas": [{"wing": "project", "room": "backend", "source_file": "api.md"}],
            "ids": ["drawer_1"],
        }

    def upsert(self, ids, documents, metadatas):
        self.upserts.append({"ids": ids, "documents": documents, "metadatas": metadatas})


class _FakeClient:
    latest = None

    def __init__(self, path):
        self.path = path
        self.main = _FakeCollection()
        self.compressed = _FakeCollection()
        _FakeClient.latest = self

    def get_collection(self, name):
        assert name == "mempalace_drawers"
        return self.main

    def get_or_create_collection(self, name):
        assert name == "mempalace_compressed"
        return self.compressed


class _FakeDialect:
    @classmethod
    def from_config(cls, _config_path):
        return cls()

    @staticmethod
    def count_tokens(text):
        return max(1, len(text) // 10)

    def compress(self, text, metadata=None):
        return f"CMP|{metadata.get('wing', '?')}|{text[:16]}"

    def compression_stats(self, _original, _compressed):
        # Modern key names from dialect.py.
        return {
            "original_tokens_est": 10,
            "summary_tokens_est": 4,
            "size_ratio": 2.5,
            "original_chars": 100,
            "summary_chars": 40,
            "note": "Estimates only",
        }


def test_cmd_compress_dry_run_accepts_modern_stats_keys(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("chromadb.PersistentClient", _FakeClient)
    monkeypatch.setattr("mempalace.dialect.Dialect", _FakeDialect)

    args = SimpleNamespace(palace=str(tmp_path / "palace"), wing=None, dry_run=True, config=None)
    cli.cmd_compress(args)

    out = capsys.readouterr().out
    assert "Compressing 1 drawers" in out
    assert "10t -> 4t (2.5x)" in out
    assert "(dry run -- nothing stored)" in out


def test_cmd_compress_persists_metadata_with_modern_stats_keys(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("chromadb.PersistentClient", _FakeClient)
    monkeypatch.setattr("mempalace.dialect.Dialect", _FakeDialect)

    args = SimpleNamespace(palace=str(tmp_path / "palace"), wing=None, dry_run=False, config=None)
    cli.cmd_compress(args)

    _ = capsys.readouterr()
    stored = _FakeClient.latest.compressed.upserts
    assert len(stored) == 1

    meta = stored[0]["metadatas"][0]
    assert meta["compression_ratio"] == 2.5
    assert meta["original_tokens"] == 10
