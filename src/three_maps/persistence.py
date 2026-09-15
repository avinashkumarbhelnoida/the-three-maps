from __future__ import annotations
import json, sqlite3, os
from datetime import datetime, timezone
from typing import Any, Protocol
from three_maps.domain.types import Analysis, AnalysisStatus, InputSnapshot, LineageRecord, AuditEvent, VersionBundle, Target

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS analyses (
 id TEXT PRIMARY KEY, owner_id TEXT, status TEXT NOT NULL, input_snapshot_id TEXT NOT NULL UNIQUE,
 version_bundle_json TEXT NOT NULL, requested_maps_json TEXT NOT NULL, target_json TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS input_snapshots (
 id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL UNIQUE REFERENCES analyses(id),
 data_json TEXT NOT NULL, created_at TEXT NOT NULL, immutable INTEGER NOT NULL CHECK(immutable=1),
 version_bundle_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS result_records (
 id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL REFERENCES analyses(id),
 result_type TEXT NOT NULL, payload_json TEXT NOT NULL, result_hash TEXT,
 created_at TEXT NOT NULL, UNIQUE(analysis_id,result_type)
);
CREATE TABLE IF NOT EXISTS lineage_records (
 id TEXT NOT NULL, analysis_id TEXT NOT NULL REFERENCES analyses(id), payload_json TEXT NOT NULL,
 created_at TEXT NOT NULL, PRIMARY KEY(id, analysis_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
 id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, analysis_id TEXT REFERENCES analyses(id),
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lineage_analysis ON lineage_records(analysis_id);
CREATE INDEX IF NOT EXISTS idx_audit_analysis ON audit_events(analysis_id);
CREATE INDEX IF NOT EXISTS idx_results_analysis ON result_records(analysis_id);
CREATE TABLE IF NOT EXISTS idempotency_keys (owner_id TEXT NOT NULL, idem_key TEXT NOT NULL, analysis_id TEXT NOT NULL REFERENCES analyses(id), created_at TEXT NOT NULL, PRIMARY KEY(owner_id, idem_key));
'''

class AnalysisRepository(Protocol):
    def save_analysis(self, analysis: Analysis, snapshot: InputSnapshot) -> None: ...
    def get_analysis(self, analysis_id: str) -> Analysis | None: ...
    def get_analysis_for_owner(self, analysis_id: str, owner_id: str) -> Analysis | None: ...
    def save_idempotency(self, owner_id: str, idem_key: str, analysis_id: str) -> bool: ...
    def get_idempotency(self, owner_id: str, idem_key: str) -> str | None: ...
    def get_snapshot(self, snapshot_id: str) -> InputSnapshot | None: ...
    def save_result(self, analysis_id: str, result_type: str, payload: dict[str, Any], result_hash: str | None = None) -> None: ...
    def get_result(self, analysis_id: str, result_type: str) -> dict[str, Any] | None: ...
    def save_lineage(self, analysis_id: str, record: LineageRecord) -> None: ...
    def get_lineage(self, analysis_id: str) -> list[LineageRecord]: ...
    def save_audit(self, analysis_id: str, event: AuditEvent) -> None: ...
    def get_audit(self, analysis_id: str) -> list[AuditEvent]: ...

class SQLiteRepository:
    """Durable adapter. Domain engines never depend on sqlite implementation details."""
    def __init__(self, path: str | None = None) -> None:
        self.path = path if path is not None else os.getenv('THE_THREE_MAPS_DB_PATH', ':memory:')
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    @staticmethod
    def _json(value: Any) -> str:
        if hasattr(value, 'model_dump'):
            value = value.model_dump(mode='json')
        return json.dumps(value, sort_keys=True, separators=(',', ':'))

    def save_analysis(self, analysis: Analysis, snapshot: InputSnapshot) -> None:
        if snapshot.immutable is not True or snapshot.analysis_id != analysis.id:
            raise ValueError('Input snapshot must be immutable and belong to analysis')
        with self.conn:
            self.conn.execute('''INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?)''', (
                analysis.id, analysis.owner_id, analysis.status.value, analysis.input_snapshot_id,
                self._json(analysis.version_bundle), self._json(analysis.requested_maps),
                self._json(analysis.target), analysis.created_at.isoformat(), analysis.updated_at.isoformat()))
            self.conn.execute('''INSERT INTO input_snapshots VALUES (?,?,?,?,?,?)''', (
                snapshot.id, snapshot.analysis_id, self._json(snapshot.data), snapshot.created_at.isoformat(), 1,
                self._json(snapshot.version_bundle)))

    def get_analysis(self, analysis_id: str) -> Analysis | None:
        r = self.conn.execute('SELECT * FROM analyses WHERE id=?', (analysis_id,)).fetchone()
        if not r: return None
        return Analysis(id=r['id'], owner_id=r['owner_id'], status=r['status'], input_snapshot_id=r['input_snapshot_id'],
            version_bundle=VersionBundle(**json.loads(r['version_bundle_json'])),
            requested_maps=json.loads(r['requested_maps_json']), target=Target(**json.loads(r['target_json'])),
            created_at=datetime.fromisoformat(r['created_at']), updated_at=datetime.fromisoformat(r['updated_at']))

    def get_analysis_for_owner(self, analysis_id: str, owner_id: str) -> Analysis | None:
        r = self.conn.execute("SELECT * FROM analyses WHERE id=? AND owner_id=?", (analysis_id, owner_id)).fetchone()
        if not r: return None
        return Analysis(id=r["id"], owner_id=r["owner_id"], status=r["status"], input_snapshot_id=r["input_snapshot_id"],
            version_bundle=VersionBundle(**json.loads(r["version_bundle_json"])), requested_maps=json.loads(r["requested_maps_json"]),
            target=Target(**json.loads(r["target_json"])), created_at=datetime.fromisoformat(r["created_at"]), updated_at=datetime.fromisoformat(r["updated_at"]))

    def save_idempotency(self, owner_id: str, idem_key: str, analysis_id: str) -> bool:
        with self.conn:
            try:
                self.conn.execute("INSERT INTO idempotency_keys VALUES (?,?,?,?)", (owner_id, idem_key, analysis_id, datetime.now(timezone.utc).isoformat()))
                return True
            except sqlite3.IntegrityError:
                return False

    def get_idempotency(self, owner_id: str, idem_key: str) -> str | None:
        r=self.conn.execute("SELECT analysis_id FROM idempotency_keys WHERE owner_id=? AND idem_key=?", (owner_id, idem_key)).fetchone()
        return None if not r else r["analysis_id"]

    def get_snapshot(self, snapshot_id: str) -> InputSnapshot | None:
        r=self.conn.execute('SELECT * FROM input_snapshots WHERE id=?',(snapshot_id,)).fetchone()
        if not r:return None
        return InputSnapshot(id=r['id'], analysis_id=r['analysis_id'], data=json.loads(r['data_json']),
            created_at=datetime.fromisoformat(r['created_at']), immutable=bool(r['immutable']),
            version_bundle=VersionBundle(**json.loads(r['version_bundle_json'])))

    def save_result(self, analysis_id: str, result_type: str, payload: dict[str, Any], result_hash: str | None=None) -> None:
        # Results are append-once: replacing an existing result is prohibited.
        with self.conn:
            self.conn.execute('INSERT INTO result_records VALUES (?,?,?,?,?,?)',
                (f'{analysis_id}:{result_type}', analysis_id, result_type, self._json(payload), result_hash, datetime.now(timezone.utc).isoformat()))

    def get_result(self, analysis_id: str, result_type: str) -> dict[str, Any] | None:
        r=self.conn.execute('SELECT * FROM result_records WHERE analysis_id=? AND result_type=?',(analysis_id,result_type)).fetchone()
        return None if not r else {'payload':json.loads(r['payload_json']), 'result_hash':r['result_hash'], 'created_at':r['created_at']}

    def save_lineage(self, analysis_id: str, record: LineageRecord) -> None:
        with self.conn:
            self.conn.execute('INSERT INTO lineage_records VALUES (?,?,?,?)',(record.id,analysis_id,self._json(record),record.timestamp.isoformat()))
    def get_lineage(self, analysis_id: str) -> list[LineageRecord]:
        rows=self.conn.execute('SELECT payload_json FROM lineage_records WHERE analysis_id=? ORDER BY created_at',(analysis_id,)).fetchall()
        return [LineageRecord(**json.loads(r['payload_json'])) for r in rows]
    def save_audit(self, analysis_id: str, event: AuditEvent) -> None:
        with self.conn:
            self.conn.execute('INSERT INTO audit_events VALUES (?,?,?,?,?)',(event.id,event.entity_id,analysis_id,self._json(event),event.timestamp.isoformat()))
    def get_audit(self, analysis_id: str) -> list[AuditEvent]:
        rows=self.conn.execute('SELECT payload_json FROM audit_events WHERE analysis_id=? ORDER BY created_at',(analysis_id,)).fetchall()
        return [AuditEvent(**json.loads(r['payload_json'])) for r in rows]
    def close(self) -> None:
        self.conn.close()
