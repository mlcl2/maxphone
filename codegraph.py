#!/usr/bin/env python3
"""
CodeGraph CLI & Architecture Graph Engine for MaxPhoneFarm Reborn
Hỗ trợ phân tích cây cú pháp, lớp (class), hàm (function), phương thức (method),
quan hệ gọi (calls), quan hệ kế thừa (inherits), quan hệ định nghĩa (defines).

Usage:
  python3 codegraph.py stats
  python3 codegraph.py find <symbol_name>
  python3 codegraph.py calls <symbol_name>
  python3 codegraph.py callers <symbol_name>
  python3 codegraph.py inspect <symbol_name>
  python3 codegraph.py rebuild
"""

import sys
import os
import re
import ast
import sqlite3
import hashlib
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CODEGRAPH_DIR = PROJECT_ROOT / ".codegraph"
DB_PATH = CODEGRAPH_DIR / "codegraph.db"

def rebuild_db():
    CODEGRAPH_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except Exception:
            pass

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.executescript('''
    CREATE TABLE schema_versions (
        version INTEGER PRIMARY KEY,
        applied_at INTEGER NOT NULL,
        description TEXT
    );
    CREATE TABLE nodes (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        name TEXT NOT NULL,
        qualified_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        language TEXT NOT NULL,
        start_line INTEGER NOT NULL,
        end_line INTEGER NOT NULL,
        start_column INTEGER NOT NULL,
        end_column INTEGER NOT NULL,
        docstring TEXT,
        signature TEXT,
        visibility TEXT,
        is_exported INTEGER DEFAULT 0,
        is_async INTEGER DEFAULT 0,
        is_static INTEGER DEFAULT 0,
        is_abstract INTEGER DEFAULT 0,
        decorators TEXT,
        type_parameters TEXT,
        updated_at INTEGER NOT NULL
    );
    CREATE TABLE edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        kind TEXT NOT NULL,
        metadata TEXT,
        line INTEGER,
        col INTEGER,
        provenance TEXT DEFAULT NULL
    );
    CREATE TABLE files (
        path TEXT PRIMARY KEY,
        content_hash TEXT NOT NULL,
        language TEXT NOT NULL,
        size INTEGER NOT NULL,
        modified_at INTEGER NOT NULL,
        indexed_at INTEGER NOT NULL,
        node_count INTEGER DEFAULT 0,
        errors TEXT
    );
    CREATE TABLE project_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at INTEGER NOT NULL
    );
    CREATE INDEX idx_nodes_kind ON nodes(kind);
    CREATE INDEX idx_nodes_name ON nodes(name);
    CREATE INDEX idx_nodes_qualified_name ON nodes(qualified_name);
    CREATE INDEX idx_nodes_file_path ON nodes(file_path);
    CREATE INDEX idx_nodes_language ON nodes(language);
    CREATE INDEX idx_edges_kind ON edges(kind);
    CREATE INDEX idx_edges_source ON edges(source);
    CREATE INDEX idx_edges_target ON edges(target);
    CREATE VIRTUAL TABLE nodes_fts USING fts5(
        id,
        name,
        qualified_name,
        docstring,
        signature,
        content='nodes',
        content_rowid='rowid'
    );
    ''')

    now = int(time.time() * 1000)
    cur.execute("INSERT INTO schema_versions VALUES (1, ?, 'Initial Schema')", (now,))
    cur.execute("INSERT INTO project_metadata VALUES ('name', 'MaxPhoneFarm Reborn', ?)", (now,))
    cur.execute("INSERT INTO project_metadata VALUES ('root', ?, ?)", (str(PROJECT_ROOT), now))

    supported_exts = {
        ".py": "python",
        ".json": "json",
        ".sql": "sql",
        ".md": "markdown"
    }

    all_files = []
    ignored_dirs = {".git", ".venv", "venv", "__pycache__", "build", "dist", ".idea", ".vscode", "backups"}

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            p = Path(root) / f
            ext = p.suffix.lower()
            if ext in supported_exts:
                all_files.append(p)

    total_nodes = 0
    total_edges = 0

    print(f"📊 Đang quét và phân tích cú pháp {len(all_files)} files trong dự án...")

    for file_path in all_files:
        rel_path = str(file_path.relative_to(PROJECT_ROOT))
        ext = file_path.suffix.lower()
        lang = supported_exts[ext]
        stat = file_path.stat()
        file_size = stat.st_size
        modified_at = int(stat.st_mtime * 1000)

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        except Exception:
            continue

        file_node_id = f"file://{rel_path}"
        cur.execute(
            "INSERT INTO nodes VALUES (?, 'File', ?, ?, ?, ?, 1, ?, 0, 0, NULL, NULL, 'public', 1, 0, 0, 0, NULL, NULL, ?)",
            (file_node_id, file_path.name, rel_path, rel_path, lang, len(content.splitlines()) or 1, now)
        )
        total_nodes += 1
        file_node_count = 1

        if lang == "python":
            try:
                tree = ast.parse(content, filename=rel_path)
                
                class CodeVisitor(ast.NodeVisitor):
                    def __init__(self):
                        self.scope_stack = []

                    def visit_ClassDef(self, node):
                        nonlocal total_nodes, total_edges, file_node_count
                        cls_name = node.name
                        scope = ".".join(self.scope_stack)
                        qname = f"{scope}.{cls_name}" if scope else cls_name
                        node_id = f"{rel_path}:{qname}"

                        doc = ast.get_docstring(node)
                        decorators = [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, 'unparse') else []

                        cur.execute(
                            "INSERT OR REPLACE INTO nodes VALUES (?, 'Class', ?, ?, ?, 'python', ?, ?, ?, ?, ?, NULL, 'public', 1, 0, 0, 0, ?, NULL, ?)",
                            (node_id, cls_name, qname, rel_path, node.lineno, getattr(node, 'end_lineno', node.lineno), node.col_offset, 0, doc, str(decorators) if decorators else None, now)
                        )
                        total_nodes += 1
                        file_node_count += 1

                        cur.execute("INSERT INTO edges (source, target, kind, line) VALUES (?, ?, 'defines', ?)", (file_node_id, node_id, node.lineno))
                        total_edges += 1

                        # Base classes inheritance
                        for base in node.bases:
                            base_name = getattr(base, 'id', None) or getattr(base, 'attr', None)
                            if base_name:
                                cur.execute("INSERT INTO edges (source, target, kind, line) VALUES (?, ?, 'inherits', ?)", (node_id, base_name, node.lineno))
                                total_edges += 1

                        self.scope_stack.append(cls_name)
                        self.generic_visit(node)
                        self.scope_stack.pop()

                    def visit_FunctionDef(self, node):
                        self._handle_func(node, is_async=0)

                    def visit_AsyncFunctionDef(self, node):
                        self._handle_func(node, is_async=1)

                    def _handle_func(self, node, is_async=0):
                        nonlocal total_nodes, total_edges, file_node_count
                        fn_name = node.name
                        scope = ".".join(self.scope_stack)
                        qname = f"{scope}.{fn_name}" if scope else fn_name
                        node_id = f"{rel_path}:{qname}"

                        doc = ast.get_docstring(node)
                        kind = "Method" if self.scope_stack else "Function"
                        args_str = ", ".join(a.arg for a in node.args.args)
                        sig = f"def {fn_name}({args_str})"
                        decorators = [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, 'unparse') else []

                        cur.execute(
                            "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?, 'python', ?, ?, ?, ?, ?, ?, 'public', 1, ?, 0, 0, ?, NULL, ?)",
                            (node_id, kind, fn_name, qname, rel_path, node.lineno, getattr(node, 'end_lineno', node.lineno), node.col_offset, 0, doc, sig, is_async, str(decorators) if decorators else None, now)
                        )
                        total_nodes += 1
                        file_node_count += 1

                        parent_id = f"{rel_path}:{scope}" if scope else file_node_id
                        cur.execute("INSERT INTO edges (source, target, kind, line) VALUES (?, ?, 'defines', ?)", (parent_id, node_id, node.lineno))
                        total_edges += 1

                        self.scope_stack.append(fn_name)
                        self.generic_visit(node)
                        self.scope_stack.pop()

                    def visit_Call(self, node):
                        nonlocal total_edges
                        func_name = None
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr

                        if func_name and self.scope_stack:
                            caller_qname = ".".join(self.scope_stack)
                            caller_id = f"{rel_path}:{caller_qname}"
                            cur.execute(
                                "INSERT INTO edges (source, target, kind, line) VALUES (?, ?, 'calls', ?)",
                                (caller_id, func_name, node.lineno)
                            )
                            total_edges += 1
                        self.generic_visit(node)

                visitor = CodeVisitor()
                visitor.visit(tree)
            except Exception:
                pass

        cur.execute(
            "INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
            (rel_path, content_hash, lang, file_size, modified_at, now, file_node_count)
        )

    # Sync FTS
    cur.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    print(f"✅ Đã dựng xong đồ thị CodeGraph cho MaxPhoneFarm Reborn!")
    print(f"   - Tổng số Nodes (Files, Classes, Functions, Methods): {total_nodes}")
    print(f"   - Tổng số Edges (Defines, Calls, Inherits): {total_edges}")
    print(f"   - Lưu tại: {DB_PATH}")

def show_stats():
    if not DB_PATH.exists():
        rebuild_db()
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    nodes_cnt = cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    edges_cnt = cur.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    files_cnt = cur.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    kinds = cur.execute("SELECT kind, COUNT(*) FROM nodes GROUP BY kind").fetchall()
    edge_kinds = cur.execute("SELECT kind, COUNT(*) FROM edges GROUP BY kind").fetchall()

    print("══════════════════════════════════════════════")
    print("📊 CODEGRAPH METRICS: MaxPhoneFarm Reborn")
    print("══════════════════════════════════════════════")
    print(f"📁 Files indexed: {files_cnt}")
    print(f"🔷 Total Nodes:   {nodes_cnt}")
    print(f"🔗 Total Edges:   {edges_cnt}")
    print("\n[Node Types Breakdown]")
    for k, c in kinds:
        print(f" - {k:12s}: {c:5d}")
    print("\n[Edge Relationships Breakdown]")
    for k, c in edge_kinds:
        print(f" - {k:12s}: {c:5d}")
    print("══════════════════════════════════════════════")
    conn.close()

def find_symbol(name):
    if not DB_PATH.exists():
        rebuild_db()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, kind, name, qualified_name, file_path, start_line, signature, docstring FROM nodes WHERE name LIKE ? OR qualified_name LIKE ? LIMIT 30",
        (f"%{name}%", f"%{name}%")
    ).fetchall()

    if not rows:
        print(f"❌ Không tìm thấy symbol nào khớp với '{name}'.")
        return

    print(f"🔍 Kết quả tìm kiếm cho '{name}' ({len(rows)} kết quả):")
    for r in rows:
        node_id, kind, sname, qname, fpath, line, sig, doc = r
        doc_snippet = f" | {doc.splitlines()[0]}" if doc else ""
        print(f"🔷 [{kind:8s}] {qname} -> {fpath}:{line}{doc_snippet}")
    conn.close()

def find_calls(name):
    if not DB_PATH.exists():
        rebuild_db()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT source, target, kind, line FROM edges WHERE (source LIKE ? OR target LIKE ?) AND kind='calls' LIMIT 40",
        (f"%{name}%", f"%{name}%")
    ).fetchall()

    if not rows:
        print(f"❌ Không tìm thấy quan hệ gọi (calls) nào liên quan đến '{name}'.")
        return

    print(f"🔗 Đồ thị gọi hàm (Call Graph) liên quan đến '{name}':")
    for r in rows:
        src, tgt, kind, line = r
        print(f"   {src} ──(gọi tại dòng {line})──▶ {tgt}()")
    conn.close()

def inspect_symbol(name):
    if not DB_PATH.exists():
        rebuild_db()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, kind, name, qualified_name, file_path, start_line, end_line, signature, docstring, decorators FROM nodes WHERE name = ? OR qualified_name = ? LIMIT 1",
        (name, name)
    ).fetchone()

    if not row:
        find_symbol(name)
        return

    node_id, kind, sname, qname, fpath, sline, eline, sig, doc, dec = row
    print("══════════════════════════════════════════════")
    print(f"🔎 CHI TIẾT SYMBOL: {qname}")
    print("══════════════════════════════════════════════")
    print(f"Loại:        {kind}")
    print(f"File:        {fpath} (dòng {sline} - {eline})")
    if sig:
        print(f"Chữ ký hàm:  {sig}")
    if dec:
        print(f"Decorators:  {dec}")
    if doc:
        print(f"Docstring:\n{doc.strip()}")

    # Outgoing calls
    calls = cur.execute("SELECT target, line FROM edges WHERE source = ? AND kind='calls'", (node_id,)).fetchall()
    if calls:
        print("\n[Các hàm/phương thức được gọi bên trong (Outgoing Calls)]:")
        for tgt, line in calls:
            print(f" - line {line:4d}: {tgt}()")

    # Incoming callers
    callers = cur.execute("SELECT source, line FROM edges WHERE target = ? AND kind='calls'", (sname,)).fetchall()
    if callers:
        print("\n[Các nơi gọi đến symbol này (Incoming Callers)]:")
        for src, line in callers:
            print(f" - {src} (line {line})")

    print("══════════════════════════════════════════════")
    conn.close()

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "rebuild":
        rebuild_db()
    elif args[0] == "stats":
        show_stats()
    elif args[0] == "find" and len(args) > 1:
        find_symbol(args[1])
    elif args[0] in ("calls", "callers") and len(args) > 1:
        find_calls(args[1])
    elif args[0] == "inspect" and len(args) > 1:
        inspect_symbol(args[1])
    else:
        print(__doc__)
