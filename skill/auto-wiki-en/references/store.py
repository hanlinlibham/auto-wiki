"""Wiki structured-data storage layer (v2 · bitemporal ontology).

Each wiki domain directory maintains one data.db (SQLite) holding all structured data.
Markdown pages handle only narrative analysis and relation edges; anything quantifiable,
time-series, state, or event goes into data.db.

Consistent with the contract wiki/{domain}/_ontology.md. Six-tier time model → three physical homes:
    T0 observations       → data_points (per-period series; period=valid-time, recorded_at=transaction-time)
    T1 states / T2 logic  → facts (bitemporal table: valid_from/valid_to/is_current; retire, never delete)
    T4 events             → events (append-only; the stamper of every state switch)
    T3 entity relations   → relations (with temporal columns; near-permanent edges keep valid_to at 9999)

Core discipline: overwriting happens only when correcting a T0 row with the same
(page,field,period,source); any change in T1/T2/T3 means "seal the old row's valid_to +
insert a new row" — never DELETE (implemented by assert_fact / retire).

Usage:
    from store import WikiStore
    store = WikiStore("wiki/macro/")
    store.init_db()
    store.upsert_page("7-day reverse repo", "7-day reverse repo", "entity", subtype="instrument")
    store.record_data("7-day reverse repo rate", "rate", 1.40, "%", "2026-05", "2026-05-25-broker-fixed-income-report")
    store.assert_fact("monetary policy toolkit", "policy rate anchor", "7-day reverse repo",
                      valid_from="2025-03", recorded_at="2026-06-07",
                      source_slug="...", caused_by_event="2025-03-MLF-reform")
    store.add_relation("7-day reverse repo", "People's Bank of China", "operated_by")

CLI:
    python store.py init wiki/macro/
    python store.py dump wiki/macro/
    python store.py asof wiki/macro/ 2024-12     — rebuild the state slice as of a date
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

FAR_FUTURE = "9999-12-31"

SCHEMA_SQL = f"""
-- Node registry. type extends to the v2 six kinds; entity is refined via subtype: institution/instrument/indicator.
CREATE TABLE IF NOT EXISTS pages (
    slug        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('source','entity','concept','event','analysis','ontology')),
    subtype     TEXT,                 -- entity: institution|instrument|indicator
    confidence  TEXT NOT NULL DEFAULT 'medium' CHECK(confidence IN ('high','medium','low','contested')),
    is_current  INTEGER NOT NULL DEFAULT 1,   -- 0 = the mechanism/state this page describes is retired (see facts)
    valid_to    TEXT DEFAULT '{FAR_FUTURE}',   -- expiry date of a mechanism page (backfilled at retirement)
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL
);

-- T0 observations: per-period series. period=valid-time; recorded_at=transaction-time (which report recorded it).
-- Same (page,field,period) corrected by a newer report → keep both rows, distinguished by recorded_at; no history shuffling.
CREATE TABLE IF NOT EXISTS data_points (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    page_slug   TEXT NOT NULL REFERENCES pages(slug),
    field       TEXT NOT NULL,
    value       REAL NOT NULL,
    unit        TEXT NOT NULL,
    period      TEXT NOT NULL,                 -- valid-time
    source_slug TEXT NOT NULL,
    recorded_at TEXT NOT NULL,                 -- transaction-time
    scope       TEXT,
    verified    INTEGER,
    confidence  TEXT DEFAULT 'high' CHECK(confidence IN ('high','medium','low','contested')),
    supersedes_id INTEGER,                     -- points to the older observation this row corrects
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(page_slug, field, period, source_slug)
);

-- T1 states + T2 durable logic: bitemporal table. Retirement = UPDATE valid_to/is_current + insert new row; never delete.
CREATE TABLE IF NOT EXISTS facts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    page_slug       TEXT NOT NULL,             -- page the proposition belongs to (carrier of the state/logic)
    predicate       TEXT NOT NULL,             -- proposition predicate, e.g. 'policy anchor' / 'holds'
    object_text     TEXT,                      -- proposition object (text/value description)
    object_slug     TEXT,                      -- if the object is another node
    valid_from      TEXT NOT NULL,             -- when it became true in the world
    valid_to        TEXT NOT NULL DEFAULT '{FAR_FUTURE}',
    is_current      INTEGER NOT NULL DEFAULT 1,
    recorded_at     TEXT NOT NULL,             -- when I recorded it
    recorded_until  TEXT NOT NULL DEFAULT '{FAR_FUTURE}',
    confidence      TEXT DEFAULT 'high',
    durability      TEXT,                      -- for T2: high|medium|low
    source_slug     TEXT,
    supersedes_id   INTEGER,                   -- chains to the predecessor assertion
    caused_by_event TEXT,                      -- which event created it
    retired_by_event TEXT,                     -- which event retired it
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- T4 events: append-only; the stamper and audit anchor of every T1 switch / T2 retirement / T3 change.
CREATE TABLE IF NOT EXISTS events (
    slug        TEXT PRIMARY KEY,
    event_date  TEXT NOT NULL,
    actor_slug  TEXT,
    description TEXT,
    source_slug TEXT,
    recorded_at TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- T3 relations: edges from the controlled vocabulary, with temporal columns. Near-permanent edges keep valid_to at 9999; retirement only stamps valid_to.
CREATE TABLE IF NOT EXISTS relations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    from_slug   TEXT NOT NULL,
    to_slug     TEXT NOT NULL,
    type        TEXT NOT NULL,
    bound_role  TEXT,                          -- for bounds: upper|lower|center
    valid_from  TEXT,
    valid_to    TEXT DEFAULT '{FAR_FUTURE}',
    recorded_at TEXT,
    retract_event_slug TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(from_slug, to_slug, type)
);

CREATE INDEX IF NOT EXISTS idx_dp_page ON data_points(page_slug);
CREATE INDEX IF NOT EXISTS idx_dp_field ON data_points(field);
CREATE INDEX IF NOT EXISTS idx_dp_period ON data_points(period);
CREATE INDEX IF NOT EXISTS idx_facts_page ON facts(page_slug);
CREATE INDEX IF NOT EXISTS idx_facts_pred ON facts(predicate);
CREATE INDEX IF NOT EXISTS idx_facts_cur ON facts(is_current);
CREATE INDEX IF NOT EXISTS idx_rel_from ON relations(from_slug);
CREATE INDEX IF NOT EXISTS idx_rel_to ON relations(to_slug);
"""


class WikiStore:
    """Bitemporal SQLite storage interface for a single domain wiki."""

    def __init__(self, wiki_dir: str | Path):
        self.wiki_dir = Path(wiki_dir)
        self.db_path = self.wiki_dir / "data.db"
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def init_db(self) -> None:
        """Create the table schema (idempotent)."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Pages ──

    def upsert_page(self, slug: str, title: str, page_type: str,
                    subtype: str = None, confidence: str = "medium",
                    is_current: int = 1, valid_to: str = FAR_FUTURE,
                    created: str = "", updated: str = "") -> None:
        today = date.today().isoformat()
        self.conn.execute("""
            INSERT INTO pages (slug, title, type, subtype, confidence, is_current, valid_to, created, updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title, type=excluded.type, subtype=excluded.subtype,
                confidence=excluded.confidence, is_current=excluded.is_current,
                valid_to=excluded.valid_to, updated=excluded.updated
        """, (slug, title, page_type, subtype, confidence, is_current, valid_to,
              created or today, updated or today))
        self.conn.commit()

    # ── T0: Data Points (observation series) ──

    def record_data(self, page_slug: str, field: str, value: float,
                    unit: str, period: str, source_slug: str,
                    recorded_at: str = None, scope: str = None,
                    verified: bool = None, confidence: str = "high") -> None:
        """Record one observation. Idempotent overwrite on the same (page,field,period,source); corrections from different sources coexist."""
        recorded_at = recorded_at or date.today().isoformat()
        v_int = None if verified is None else (1 if verified else 0)
        self.conn.execute("""
            INSERT INTO data_points (page_slug, field, value, unit, period, source_slug, recorded_at, scope, verified, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(page_slug, field, period, source_slug) DO UPDATE SET
                value=excluded.value, unit=excluded.unit, recorded_at=excluded.recorded_at,
                scope=excluded.scope, verified=excluded.verified, confidence=excluded.confidence
        """, (page_slug, field, value, unit, period, source_slug, recorded_at, scope, v_int, confidence))
        self.conn.commit()

    # Backward-compatible API name
    def upsert_data(self, *a, **k):
        return self.record_data(*a, **k)

    # ── T1/T2: Facts (state/logic temporal chain; retire, never delete) ──

    def assert_fact(self, page_slug: str, predicate: str, object_text: str,
                    valid_from: str, recorded_at: str, source_slug: str = None,
                    object_slug: str = None, confidence: str = "high",
                    durability: str = None, caused_by_event: str = None) -> Optional[int]:
        """Assert one T1 state / T2 logic. If (page,predicate) already has a current assertion, retire it first (seal valid_to + stamp the event), then insert the new row. Never delete. Returns the retired old row's id."""
        cur = self.conn.execute(
            "SELECT id FROM facts WHERE page_slug=? AND predicate=? AND is_current=1",
            (page_slug, predicate)).fetchone()
        supersedes = None
        if cur:
            supersedes = cur["id"]
            self.conn.execute(
                "UPDATE facts SET valid_to=?, is_current=0, retired_by_event=? WHERE id=?",
                (valid_from, caused_by_event, cur["id"]))
        self.conn.execute("""
            INSERT INTO facts (page_slug, predicate, object_text, object_slug, valid_from,
                is_current, recorded_at, confidence, durability, source_slug, supersedes_id, caused_by_event)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
        """, (page_slug, predicate, object_text, object_slug, valid_from, recorded_at,
              confidence, durability, source_slug, supersedes, caused_by_event))
        self.conn.commit()
        return supersedes

    # ── T4: Events ──

    def add_event(self, slug: str, event_date: str, actor_slug: str = None,
                  description: str = None, source_slug: str = None,
                  recorded_at: str = None) -> None:
        recorded_at = recorded_at or date.today().isoformat()
        self.conn.execute("""
            INSERT INTO events (slug, event_date, actor_slug, description, source_slug, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                event_date=excluded.event_date, actor_slug=excluded.actor_slug,
                description=excluded.description
        """, (slug, event_date, actor_slug, description, source_slug, recorded_at))
        self.conn.commit()

    # ── T3: Relations ──

    def add_relation(self, from_slug: str, to_slug: str, rel_type: str,
                     bound_role: str = None, valid_from: str = None,
                     recorded_at: str = None) -> None:
        self.conn.execute("""
            INSERT OR IGNORE INTO relations (from_slug, to_slug, type, bound_role, valid_from, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (from_slug, to_slug, rel_type, bound_role, valid_from,
              recorded_at or date.today().isoformat()))
        self.conn.commit()

    def retire_relation(self, from_slug: str, to_slug: str, rel_type: str,
                        valid_to: str, event_slug: str = None) -> None:
        self.conn.execute(
            "UPDATE relations SET valid_to=?, retract_event_slug=? WHERE from_slug=? AND to_slug=? AND type=?",
            (valid_to, event_slug, from_slug, to_slug, rel_type))
        self.conn.commit()

    # ── Queries ──

    def query_data(self, page_slug: str = None, field: str = None) -> list[dict]:
        sql = "SELECT * FROM data_points WHERE 1=1"
        params: list = []
        if page_slug:
            sql += " AND page_slug=?"; params.append(page_slug)
        if field:
            sql += " AND field=?"; params.append(field)
        sql += " ORDER BY period DESC, recorded_at DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def latest_value(self, page_slug: str, field: str, as_of_period: str = None) -> Optional[dict]:
        """T0 slice: latest observation up to a given period (taking the most recent recorded_at within that period)."""
        sql = "SELECT * FROM data_points WHERE page_slug=? AND field=?"
        params: list = [page_slug, field]
        if as_of_period:
            sql += " AND period<=?"; params.append(as_of_period)
        sql += " ORDER BY period DESC, recorded_at DESC LIMIT 1"
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def current_facts(self, page_slug: str = None) -> list[dict]:
        sql = "SELECT * FROM facts WHERE is_current=1"
        params: list = []
        if page_slug:
            sql += " AND page_slug=?"; params.append(page_slug)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def facts_as_of(self, as_of: str, page_slug: str = None) -> list[dict]:
        """T1/T2 time travel: rebuild all states/logic true on as_of (valid_from<=as_of<valid_to)."""
        sql = "SELECT * FROM facts WHERE valid_from<=? AND valid_to>?"
        params: list = [as_of, as_of]
        if page_slug:
            sql += " AND page_slug=?"; params.append(page_slug)
        sql += " ORDER BY page_slug, predicate"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def query_relations(self, slug: str = None, rel_type: str = None) -> list[dict]:
        sql = "SELECT * FROM relations WHERE 1=1"
        params: list = []
        if slug:
            sql += " AND (from_slug=? OR to_slug=?)"; params += [slug, slug]
        if rel_type:
            sql += " AND type=?"; params.append(rel_type)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def get_page(self, slug: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM pages WHERE slug=?", (slug,)).fetchone()
        return dict(row) if row else None

    def list_pages(self, page_type: str = None) -> list[dict]:
        sql = "SELECT * FROM pages"
        params: list = []
        if page_type:
            sql += " WHERE type=?"; params.append(page_type)
        sql += " ORDER BY updated DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def stats(self) -> dict:
        s: dict[str, Any] = {}
        s["pages"] = self.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        s["data_points"] = self.conn.execute("SELECT COUNT(*) FROM data_points").fetchone()[0]
        s["facts"] = self.conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        s["facts_current"] = self.conn.execute("SELECT COUNT(*) FROM facts WHERE is_current=1").fetchone()[0]
        s["facts_retired"] = self.conn.execute("SELECT COUNT(*) FROM facts WHERE is_current=0").fetchone()[0]
        s["events"] = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        s["relations"] = self.conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
        s["contested_pages"] = self.conn.execute("SELECT COUNT(*) FROM pages WHERE confidence='contested'").fetchone()[0]
        for row in self.conn.execute(
                "SELECT type, COALESCE(subtype,'') AS st, COUNT(*) as cnt FROM pages GROUP BY type, subtype").fetchall():
            label = f"{row['type']}/{row['st']}" if row["st"] else row["type"]
            s[f"pages_{label}"] = row["cnt"]
        return s

    def dump(self) -> str:
        st = self.stats()
        lines = [
            f"Wiki Store: {self.wiki_dir.name}",
            "=" * 56,
            f"Pages: {st['pages']} | DataPoints: {st['data_points']} | "
            f"Facts: {st['facts']} (current {st['facts_current']}, retired {st['facts_retired']}) | "
            f"Events: {st['events']} | Relations: {st['relations']}",
            "",
            "Pages by type:",
        ]
        for k, v in sorted(st.items()):
            if k.startswith("pages_"):
                lines.append(f"  {k[6:]}: {v}")

        cur = self.conn.execute(
            "SELECT page_slug, predicate, object_text, valid_from FROM facts WHERE is_current=1 ORDER BY page_slug LIMIT 12"
        ).fetchall()
        if cur:
            lines += ["", "Current facts (T1/T2):"]
            for r in cur:
                lines.append(f"  [{r['page_slug']}] {r['predicate']} = {r['object_text']} (since {r['valid_from']})")

        retired = self.conn.execute(
            "SELECT page_slug, predicate, object_text, valid_from, valid_to, retired_by_event FROM facts WHERE is_current=0"
        ).fetchall()
        if retired:
            lines += ["", "Retired facts (retire, never delete):"]
            for r in retired:
                lines.append(f"  [{r['page_slug']}] {r['predicate']} = {r['object_text']} "
                             f"({r['valid_from']}→{r['valid_to']}, by {r['retired_by_event']})")

        rels = self.conn.execute("SELECT from_slug, type, to_slug, bound_role FROM relations LIMIT 14").fetchall()
        if rels:
            lines += ["", "Relations:"]
            for r in rels:
                role = f" [{r['bound_role']}]" if r["bound_role"] else ""
                lines.append(f"  {r['from_slug']} --{r['type']}{role}--> {r['to_slug']}")

        return "\n".join(lines)


# ── CLI ──

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python store.py init <wiki_dir>")
        print("  python store.py dump <wiki_dir>")
        print("  python store.py asof <wiki_dir> <YYYY-MM>   — rebuild the state slice as of a date")
        sys.exit(1)

    cmd, target = sys.argv[1], Path(sys.argv[2])
    store = WikiStore(target)

    if cmd == "init":
        store.init_db()
        print(f"Initialized: {store.db_path}")
    elif cmd == "dump":
        if not store.db_path.exists():
            print(f"No data.db found in {target}"); sys.exit(1)
        print(store.dump())
    elif cmd == "asof":
        if len(sys.argv) < 4:
            print("asof needs a date, e.g. 2024-12"); sys.exit(1)
        as_of = sys.argv[3]
        print(f"== State slice as of {as_of} ==")
        for f in store.facts_as_of(as_of):
            print(f"  [{f['page_slug']}] {f['predicate']} = {f['object_text']} "
                  f"(valid {f['valid_from']}→{f['valid_to']})")
    else:
        print(f"Unknown command: {cmd}"); sys.exit(1)

    store.close()


if __name__ == "__main__":
    main()
