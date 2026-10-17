"""Internal change metadata for future sync; deliberately no public sync endpoint."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

TABLES = {
    "app": (
        "conversations",
        "messages",
        "content_items",
        "tags",
        "document_tags",
        "knowledge_folders",
        "folder_tags",
        "tasks",
        "feed_manual_items",
        "feed_hidden_items",
        "feed_saves",
        "app_preferences",
        "appearance_assets",
        "appearance_settings",
    ),
    "automation": ("automations", "automation_runs"),
}


class ChangeJournal:
    def __init__(self, directory: Path, workspace_id: str):
        self.directory, self.workspace_id = directory, workspace_id

    @contextmanager
    def _connect(self, domain):
        if domain not in TABLES:
            raise ValueError("unknown change domain")
        db = sqlite3.connect(self.directory / f"{domain}.sqlite3", timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _verify(self, db):
        row = db.execute("SELECT workspace_id FROM cloud_workspace WHERE singleton=1").fetchone()
        if row is None or row[0] != self.workspace_id:
            raise ValueError("workspace database identity mismatch")

    @staticmethod
    def _key(columns, prefix=""):
        fields = [f'{prefix}"{column}"' for column in columns]
        return (
            f"CAST({fields[0]} AS TEXT)" if len(fields) == 1 else f"json_array({','.join(fields)})"
        )

    @staticmethod
    def _record_sql(table, key, deleted):
        # Table names and expressions come only from the fixed schema allowlist.
        return f"""
            INSERT INTO cloud_entity_versions(entity_type,entity_id,version,deleted)
            VALUES('{table}',{key},1,{deleted})
            ON CONFLICT(entity_type,entity_id) DO UPDATE SET
                version=version+1,deleted=excluded.deleted;
            INSERT INTO cloud_changes(entity_type,entity_id,version,deleted)
            SELECT entity_type,entity_id,version,deleted FROM cloud_entity_versions
                WHERE entity_type='{table}' AND entity_id={key};
        """

    def install(self):
        for domain, tables in TABLES.items():
            if not (self.directory / f"{domain}.sqlite3").exists():
                continue
            with self._connect(domain) as db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS cloud_workspace(
                        singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                        workspace_id TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS cloud_entity_versions(
                        entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,
                        version INTEGER NOT NULL,deleted INTEGER NOT NULL,
                        PRIMARY KEY(entity_type,entity_id));
                    CREATE TABLE IF NOT EXISTS cloud_changes(
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,entity_type TEXT NOT NULL,
                        entity_id TEXT NOT NULL,version INTEGER NOT NULL,deleted INTEGER NOT NULL,
                        changed_at TEXT NOT NULL DEFAULT(strftime('%Y-%m-%dT%H:%M:%fZ','now')));
                """)
                db.execute(
                    "INSERT OR IGNORE INTO cloud_workspace VALUES(1,?)", (self.workspace_id,)
                )
                self._verify(db)
                for table in tables:
                    schema = db.execute(f'PRAGMA table_info("{table}")').fetchall()
                    columns = [
                        row["name"] for row in sorted(schema, key=lambda r: r["pk"]) if row["pk"]
                    ]
                    if not columns:
                        continue
                    for operation in ("INSERT", "UPDATE", "DELETE"):
                        key = self._key(columns, "OLD." if operation == "DELETE" else "NEW.")
                        sql = self._record_sql(table, key, int(operation == "DELETE"))
                        db.executescript(f"""CREATE TRIGGER IF NOT EXISTS cloud_{table}_{operation}
                            AFTER {operation} ON "{table}" BEGIN {sql} END;""")
                    # One baseline for pre-existing records; repeat initialization is inert.
                    key = self._key(columns)
                    db.execute(f"""INSERT OR IGNORE INTO cloud_entity_versions
                        SELECT '{table}',{key},1,0 FROM "{table}"
                    """)
                    db.execute(
                        """INSERT INTO cloud_changes(entity_type,entity_id,version,deleted)
                        SELECT v.entity_type,v.entity_id,v.version,v.deleted
                        FROM cloud_entity_versions v WHERE v.entity_type=? AND NOT EXISTS(
                            SELECT 1 FROM cloud_changes c WHERE c.entity_type=v.entity_type
                                AND c.entity_id=v.entity_id AND c.version=v.version)""",
                        (table,),
                    )

    def record_file(self, entity_id="models", *, initial=False):
        with self._connect("app") as db:
            self._verify(db)
            if initial:
                db.execute(
                    "INSERT OR IGNORE INTO cloud_entity_versions VALUES('model_settings',?,1,0)",
                    (entity_id,),
                )
            else:
                db.execute(
                    """INSERT INTO cloud_entity_versions VALUES('model_settings',?,1,0)
                    ON CONFLICT(entity_type,entity_id) DO UPDATE SET version=version+1,deleted=0""",
                    (entity_id,),
                )
            db.execute(
                """INSERT INTO cloud_changes(entity_type,entity_id,version,deleted)
                SELECT entity_type,entity_id,version,deleted FROM cloud_entity_versions
                WHERE entity_type='model_settings' AND entity_id=? AND NOT EXISTS(
                    SELECT 1 FROM cloud_changes c WHERE c.entity_type='model_settings'
                        AND c.entity_id=cloud_entity_versions.entity_id
                        AND c.version=cloud_entity_versions.version)""",
                (entity_id,),
            )

    def events(self, *, domain="app", after=0):
        with self._connect(domain) as db:
            self._verify(db)
            return [
                {
                    **dict(row),
                    "deleted": bool(row["deleted"]),
                    "workspace_id": self.workspace_id,
                    "domain": domain,
                }
                for row in db.execute(
                    "SELECT * FROM cloud_changes WHERE seq>? ORDER BY seq", (after,)
                )
            ]
