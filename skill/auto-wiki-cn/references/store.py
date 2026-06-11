"""Wiki 结构化数据存储层（v2 · 双时态本体）。

每个 wiki 领域目录下维护一个 data.db（SQLite），存储所有结构化数据。
Markdown 页面只负责叙事分析与关系连边；可量化/可时序/状态/事件全部进 data.db。

与契约 wiki/{domain}/_ontology.md 一致。六档时间模型 → 三类物理落点：
    T0 观测值          → data_points（逐期时序，period=valid-time，recorded_at=transaction-time）
    T1 状态 / T2 逻辑  → facts（双时态拉链表：valid_from/valid_to/is_current，退役不删除）
    T4 事件            → events（append-only，所有状态切换的盖章者）
    T3 实体关系        → relations（带时态列，近永久边 valid_to 留 9999）

核心纪律：覆盖只在 T0 同 (page,field,period,source) 纠错时发生；T1/T2/T3 任何变化
都是"旧行封 valid_to + 插新行"，永不 DELETE（assert_fact / retire 实现）。

用法：
    from store import WikiStore
    store = WikiStore("wiki/macro/")
    store.init_db()
    store.upsert_page("7天逆回购", "7天逆回购", "entity", subtype="instrument")
    store.record_data("7天逆回购利率", "利率", 1.40, "%", "2026-05", "2026-05-25-某券商固收报告")
    store.assert_fact("政策利率锚", "锚工具", "7天逆回购",
                      valid_from="2025-03", recorded_at="2026-06-07",
                      source_slug="...", caused_by_event="2025-03-MLF改革")
    store.add_relation("7天逆回购", "中国人民银行", "operated_by")

CLI:
    python store.py init wiki/macro/
    python store.py dump wiki/macro/
    python store.py asof wiki/macro/ 2024-12     — 重建某日的状态切片
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

FAR_FUTURE = "9999-12-31"

SCHEMA_SQL = f"""
-- 节点登记表。type 扩展到 v2 六类；entity 用 subtype 细分 机构/工具/指标。
CREATE TABLE IF NOT EXISTS pages (
    slug        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('source','entity','concept','event','analysis','ontology')),
    subtype     TEXT,                 -- entity: institution|instrument|indicator
    confidence  TEXT NOT NULL DEFAULT 'medium' CHECK(confidence IN ('high','medium','low','contested')),
    is_current  INTEGER NOT NULL DEFAULT 1,   -- 0 = 该页所述机制/状态已退役（见 facts）
    valid_to    TEXT DEFAULT '{FAR_FUTURE}',   -- 机制页失效日（退役时回填）
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL
);

-- T0 观测值：逐期时序。period=valid-time；recorded_at=transaction-time（哪份研报记的）。
-- 同 (page,field,period) 被新研报修正 → 保留两行靠 recorded_at 区分，不搬 history。
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
    supersedes_id INTEGER,                     -- 指向被本行修正的旧观测
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(page_slug, field, period, source_slug)
);

-- T1 状态 + T2 耐用逻辑：双时态拉链表。退役 = UPDATE valid_to/is_current + 插新行，永不删。
CREATE TABLE IF NOT EXISTS facts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    page_slug       TEXT NOT NULL,             -- 命题所属页（状态/逻辑的承载页）
    predicate       TEXT NOT NULL,             -- 命题谓词，如 'policy_anchor' / 'holds'
    object_text     TEXT,                      -- 命题宾语（文本/数值描述）
    object_slug     TEXT,                      -- 若宾语是另一节点
    valid_from      TEXT NOT NULL,             -- 世界上何时起为真
    valid_to        TEXT NOT NULL DEFAULT '{FAR_FUTURE}',
    is_current      INTEGER NOT NULL DEFAULT 1,
    recorded_at     TEXT NOT NULL,             -- 我何时记入
    recorded_until  TEXT NOT NULL DEFAULT '{FAR_FUTURE}',
    confidence      TEXT DEFAULT 'high',
    durability      TEXT,                      -- T2 用：high|medium|low
    source_slug     TEXT,
    supersedes_id   INTEGER,                   -- 串接前任断言
    caused_by_event TEXT,                      -- 哪个事件创设了它
    retired_by_event TEXT,                     -- 哪个事件退役了它
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- T4 事件：append-only，所有 T1 切换 / T2 退役 / T3 变更的盖章者与审计锚。
CREATE TABLE IF NOT EXISTS events (
    slug        TEXT PRIMARY KEY,
    event_date  TEXT NOT NULL,
    actor_slug  TEXT,
    description TEXT,
    source_slug TEXT,
    recorded_at TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- T3 关系：受控词表的边，带时态。近永久边 valid_to 留 9999；退役只盖 valid_to。
CREATE TABLE IF NOT EXISTS relations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    from_slug   TEXT NOT NULL,
    to_slug     TEXT NOT NULL,
    type        TEXT NOT NULL,
    bound_role  TEXT,                          -- bounds 用：upper|lower|center
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
    """单个领域 wiki 的双时态 SQLite 存储接口。"""

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
        """创建表结构（幂等）。"""
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

    # ── T0: Data Points（观测值时序） ──

    def record_data(self, page_slug: str, field: str, value: float,
                    unit: str, period: str, source_slug: str,
                    recorded_at: str = None, scope: str = None,
                    verified: bool = None, confidence: str = "high") -> None:
        """记一条观测值。同 (page,field,period,source) 幂等覆盖；不同 source 的修正值并存。"""
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

    # 兼容旧 API 名
    def upsert_data(self, *a, **k):
        return self.record_data(*a, **k)

    # ── T1/T2: Facts（状态/逻辑拉链，退役不删除） ──

    def assert_fact(self, page_slug: str, predicate: str, object_text: str,
                    valid_from: str, recorded_at: str, source_slug: str = None,
                    object_slug: str = None, confidence: str = "high",
                    durability: str = None, caused_by_event: str = None) -> Optional[int]:
        """断言一条 T1 状态 / T2 逻辑。若 (page,predicate) 已有 current 断言，先退役它（封 valid_to + 盖事件），再插新行。永不删除。返回被退役的旧行 id。"""
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
        """T0 切片：截至某 period 的最新观测值（取该 period 最近 recorded_at）。"""
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
        """T1/T2 时间旅行：重建 as_of 那天为真的所有状态/逻辑（valid_from<=as_of<valid_to）。"""
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
            lines += ["", "Retired facts (退役不删除):"]
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
        print("  python store.py asof <wiki_dir> <YYYY-MM>   — 重建某日状态切片")
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
        print(f"== 状态切片 as of {as_of} ==")
        for f in store.facts_as_of(as_of):
            print(f"  [{f['page_slug']}] {f['predicate']} = {f['object_text']} "
                  f"(valid {f['valid_from']}→{f['valid_to']})")
    else:
        print(f"Unknown command: {cmd}"); sys.exit(1)

    store.close()


if __name__ == "__main__":
    main()
