#!/usr/bin/env python3
import subprocess
import sys
import re

DB_IN = 'db.sqlite3'
OUT = 'db.postgres.sql'


def run_dump(db=DB_IN):
    try:
        p = subprocess.run(['sqlite3', db, '.dump'], capture_output=True, text=True, check=True)
        return p.stdout.splitlines()
    except FileNotFoundError:
        print('sqlite3 not found on PATH. Install sqlite3 to use this script.', file=sys.stderr)
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        print('Error running sqlite3 dump:', e, file=sys.stderr)
        sys.exit(1)


def process_create(stmt):
    # stmt is the full CREATE TABLE block as a string
    s = stmt
    # remove literal AUTOINCREMENT tokens first
    s = s.replace('AUTOINCREMENT', '')
    # convert datetime column types
    s = re.sub(r"\bdatetime\b", 'timestamp with time zone', s, flags=re.IGNORECASE)
    # Replace INTEGER PRIMARY KEY with SERIAL PRIMARY KEY
    s = re.sub(r"INTEGER\s+PRIMARY\s+KEY(\s+AUTOINCREMENT)?", 'SERIAL PRIMARY KEY', s, flags=re.IGNORECASE)
    # Remove SQLite-specific WITHOUT ROWID
    s = re.sub(r"WITHOUT\s+ROWID", '', s, flags=re.IGNORECASE)
    # Remove redundant CONSTRAINT names that include sqlite_autoindex (optional)
    s = re.sub(r'\s+CONSTRAINT\s+"sqlite_autoindex[^"]+"', '', s)
    # Remove SQLite JSON_VALID check constraints
    # Convert text columns with JSON_VALID checks into jsonb
    s = re.sub(r'"([^\"]+)"\s+text\s+NOT\s+NULL\s+CHECK\s*\([^\)]*JSON_VALID[^\)]*\)', r'"\1" jsonb', s, flags=re.IGNORECASE)
    s = re.sub(r'"([^\"]+)"\s+text\s+NULL\s+CHECK\s*\([^\)]*JSON_VALID[^\)]*\)', r'"\1" jsonb NULL', s, flags=re.IGNORECASE)
    # Remove any remaining JSON_VALID checks
    s = re.sub(r'CHECK\s*\([^\)]*JSON_VALID[^\)]*\)', '', s, flags=re.IGNORECASE)
    # Remove leftover 'OR "col" IS NULL' fragments after jsonb conversion
    s = re.sub(r'jsonb\s+OR\s+"[^"]+"\s+IS\s+NULL', 'jsonb', s, flags=re.IGNORECASE)
    s = re.sub(r'jsonb\s+NULL\s+OR\s+"[^"]+"\s+IS\s+NULL', 'jsonb NULL', s, flags=re.IGNORECASE)
    # collapse redundant closing parens after jsonb substitutions
    s = re.sub(r'jsonb\s*\)+', 'jsonb', s, flags=re.IGNORECASE)
    # remove duplicated closing parentheses sequences that remain after removing CHECKs
    s = re.sub(r'\)\s*\)\s*\)', ')', s)
    s = re.sub(r'\)\s*\)\s*;', ');', s)
    s = re.sub(r'\)\s*\)\s*,', '),', s)
    # remove 'unsigned' tokens (Postgres doesn't support unsigned types)
    s = re.sub(r'\bunsigned\b', '', s, flags=re.IGNORECASE)
    # convert BLOB to bytea
    s = re.sub(r'\bBLOB\b', 'bytea', s, flags=re.IGNORECASE)
    # ensure UNIQUE/CONSTRAINT lines inside CREATE TABLE end with an extra ')' before the semicolon
    s = re.sub(r'(CONSTRAINT\s+"[^"]+"\s+UNIQUE\s*\([^)]*\))\s*;', r"\1);", s)
    # ensure REFERENCES column declarations that end the CREATE TABLE have the closing ')' before ';'
    s = re.sub(r'(REFERENCES\s+"?[^\(;]+"?\s*\([^)]*\))\s*;', r"\1);", s)
    # Normalize boolean defaults (SQLite uses 0/1)
    s = re.sub(r'((?:bool|boolean)[^,\)]*?)DEFAULT\s+1', lambda m: m.group(1) + 'DEFAULT true', s, flags=re.IGNORECASE)
    s = re.sub(r'((?:bool|boolean)[^,\)]*?)DEFAULT\s+0', lambda m: m.group(1) + 'DEFAULT false', s, flags=re.IGNORECASE)
    # Ensure the statement ends with a semicolon
    if not s.strip().endswith(';'):
        s = s + ';'
    return s


def transform(lines):
    create_blocks = []
    rest = []
    create_stmt = []
    in_create = False
    for ln in lines:
        # skip pragmas and transaction markers
        if ln.startswith('PRAGMA') or ln.startswith('BEGIN TRANSACTION') or ln.startswith('COMMIT'):
            continue
        # skip sqlite_sequence table inserts (we'll rely on SERIAL sequences)
        if ln.startswith('INSERT INTO "sqlite_sequence"'):
            continue

        # collect multi-line CREATE TABLE statements to rewrite AUTOINCREMENT
        if ln.lstrip().upper().startswith('CREATE TABLE'):
            in_create = True
            create_stmt = [ln]
            # if creation ends on same line, handle below
            if ln.rstrip().endswith(');'):
                in_create = False
                create_blocks.append(process_create('\n'.join(create_stmt)))
                create_stmt = []
            continue

        if in_create:
            create_stmt.append(ln)
            if ln.rstrip().endswith(');'):
                in_create = False
                create_blocks.append(process_create('\n'.join(create_stmt)))
                create_stmt = []
            continue

        # general replacements for non-CREATE lines
        ln = ln.replace('AUTOINCREMENT', '')
        ln = re.sub(r"\bdatetime\b", 'timestamp with time zone', ln, flags=re.IGNORECASE)
        # convert text columns with JSON_VALID checks into jsonb
        ln = re.sub(r'"([^\"]+)"\s+text\s+NOT\s+NULL\s+CHECK\s*\([^\)]*JSON_VALID[^\)]*\)', r'"\1" jsonb', ln, flags=re.IGNORECASE)
        ln = re.sub(r'"([^\"]+)"\s+text\s+NULL\s+CHECK\s*\([^\)]*JSON_VALID[^\)]*\)', r'"\1" jsonb NULL', ln, flags=re.IGNORECASE)
        # remove any remaining JSON_VALID checks
        ln = re.sub(r'CHECK\s*\([^\)]*JSON_VALID[^\)]*\)', '', ln, flags=re.IGNORECASE)
        # remove leftover 'OR "col" IS NULL' fragments after jsonb conversion
        ln = re.sub(r'jsonb\s+OR\s+"[^"]+"\s+IS\s+NULL', 'jsonb', ln, flags=re.IGNORECASE)
        ln = re.sub(r'jsonb\s+NULL\s+OR\s+"[^"]+"\s+IS\s+NULL', 'jsonb NULL', ln, flags=re.IGNORECASE)
        # collapse redundant closing parens after jsonb substitutions
        ln = re.sub(r'jsonb\s*\)+', 'jsonb', ln, flags=re.IGNORECASE)
        # remove duplicated closing parentheses sequences that remain after removing CHECKs
        ln = re.sub(r'\)\s*\)\s*\)', ')', ln)
        ln = re.sub(r'\)\s*\)\s*;', ');', ln)
        ln = re.sub(r'\)\s*\)\s*,', '),', ln)
        # remove 'unsigned' tokens in per-line processing
        ln = re.sub(r'\bunsigned\b', '', ln, flags=re.IGNORECASE)
        # convert BLOB to bytea in per-line processing
        ln = re.sub(r'\bBLOB\b', 'bytea', ln, flags=re.IGNORECASE)
        # ensure per-line UNIQUE constraints are closed properly
        ln = re.sub(r'(CONSTRAINT\s+"[^"]+"\s+UNIQUE\s*\([^)]*\))\s*;', r"\1);", ln)
        # ensure per-line REFERENCES declarations that end CREATE TABLE have closing paren
        ln = re.sub(r'(REFERENCES\s+"?[^\(;]+"?\s*\([^)]*\))\s*;', r"\1);", ln)
        # Normalize boolean defaults on non-CREATE lines too
        ln = re.sub(r'((?:bool|boolean)[^,\)]*?)DEFAULT\s+1', lambda m: m.group(1) + 'DEFAULT true', ln, flags=re.IGNORECASE)
        ln = re.sub(r'((?:bool|boolean)[^,\)]*?)DEFAULT\s+0', lambda m: m.group(1) + 'DEFAULT false', ln, flags=re.IGNORECASE)
        rest.append(ln)

    # reorder create_blocks so referenced tables exist before dependents
    def reorder_create_blocks(blocks):
        name_re = re.compile(r'CREATE TABLE (?:IF NOT EXISTS )?"([^\"]+)"', re.IGNORECASE)
        ref_re = re.compile(r'REFERENCES\s+"([^\"]+)"', re.IGNORECASE)
        nodes = {}
        for b in blocks:
            first_line = b.splitlines()[0]
            m = name_re.search(first_line)
            name = m.group(1) if m else None
            refs = set(ref_re.findall(b))
            nodes[name] = {'block': b, 'refs': refs}

        ordered = []
        # Kahn's algorithm
        while nodes:
            # find nodes with no refs or refs not in nodes
            ready = [n for n, v in nodes.items() if not (v['refs'] & set(nodes.keys()))]
            if not ready:
                # cycle detected — append remaining in arbitrary order
                ordered.extend([v['block'] for v in nodes.values()])
                break
            for n in ready:
                ordered.append(nodes[n]['block'])
                del nodes[n]

        return ordered

    ordered_creates = reorder_create_blocks(create_blocks)

    out = []
    out.extend(ordered_creates)
    out.extend(rest)
    return out


def main():
    lines = run_dump()
    out = transform(lines)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('-- Converted SQLite dump to PostgreSQL-ish SQL\n')
        f.write('-- Manual review recommended before importing into Postgres\n\n')
        f.write("SET session_replication_role = 'replica';\n\n")
        for l in out:
            f.write(l + '\n')
        f.write('\nSET session_replication_role = origin;\n')

    print('Wrote', OUT)


if __name__ == '__main__':
    main()

