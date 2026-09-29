#!/usr/bin/env python3
"""tune-project.py — tune a cat-herder scaffold to the project it was installed into.

Tuning is part of install: ./install.sh runs this after scaffolding. It can also be re-run by
hand at any time (e.g. after the codebase grows a new language or directory).

EXISTING project  -> detects languages (manifests + source-file census), the directory layout
                     actually in use (conventional per-language roots AND non-conventional
                     top-level dirs holding source), test/ui/migration roots, monorepo
                     workspaces, frameworks, database, Docker, and the test/lint/type-check/format
                     commands the project has EVIDENCE for (config files, dependencies,
                     package.json scripts, Makefile targets). A command with no evidence is left
                     "—" rather than invented.
FROM-SCRATCH      -> nothing to detect, so it prompts for the details (name, languages, package,
                     frameworks, database, UI dir, target OS), proposes the conventional layout
                     for the chosen language(s), marks the stack's idiomatic commands as
                     *proposed*, and optionally creates the directory skeleton.
ALREADY TUNED     -> a PROJECT_PROFILE.md whose stack is filled is never rewritten; the script
                     reports what it detects so drift is visible.

Writes (never clobbering project-authored values):
  .claude/PROJECT_PROFILE.md  — fills only fields still holding a `{…}` placeholder or a
                                template default, and records the detection evidence in an
                                `Install detection` section
  .claude/hooks/hooks.env     — generated from the detected layout when absent or still identical
                                to hooks.env.example; otherwise preserved (detected values printed)

It deliberately does NOT expand placeholders in CLAUDE.md / .mcp.json / workflow docs — those
carry prose that mentions the placeholders literally; the agent finishes that step
(docs/ONBOARDING.md).

Usage:
  scripts/tune-project.py [--root DIR] [--name N] [--description D] [--lang py,ts]
                          [--package P] [--db postgres] [--ui ui] [--os "Ubuntu 24.04"]
                          [--no-prompt] [--skeleton | --no-skeleton] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - older interpreters fall back to regex extraction
    tomllib = None  # type: ignore[assignment]

# --------------------------------------------------------------------------------------------
# Language knowledge base.
#   src/tests  conventional layouts, in preference order; `{pkg}` = package/module name
#   cmds       idiomatic (command, evidence) pairs. evidence None = ships with the toolchain;
#              otherwise a list of markers, any one of which proves the tool is set up:
#              a repo-relative path/glob, or "dep:<word>" found in the manifests.
# Commands run inside the dev container when the project has docker compose, else on the host.
# --------------------------------------------------------------------------------------------
PY_CFG = ["pyproject.toml", "setup.cfg", "tox.ini"]
LANGS: dict[str, dict] = {
    "python": {
        "label": "Python", "manifests": ["pyproject.toml", "setup.py", "setup.cfg",
                                         "requirements.txt", "Pipfile"],
        "exts": [".py"], "class_exts": ["py"],
        "src": ["src/{pkg}", "{pkg}", "src"], "tests": ["tests", "test"],
        "cmds": {
            "test": ("{py} -m pytest -v", ["pytest.ini", "conftest.py", "tests/conftest.py",
                                           "tests/test_*.py", "test/test_*.py", "dep:pytest"]),
            "lint": ("{py} -m ruff check .", ["ruff.toml", ".ruff.toml", "dep:ruff"]),
            "type": ("{py} -m mypy {src}", ["mypy.ini", ".mypy.ini", "dep:mypy"]),
            "format": ("{py} -m black --check . --line-length 100", ["dep:black"]),
        },
    },
    "typescript": {
        "label": "TypeScript", "manifests": ["tsconfig.json"],
        "exts": [".ts", ".tsx"], "class_exts": ["ts", "tsx"],
        "src": ["src"], "tests": ["tests", "test", "__tests__", "e2e"],
        "cmds": {
            "test": ("npx vitest run", ["vitest.config.*", "dep:vitest"]),
            "lint": ("npx eslint .", ["eslint.config.*", ".eslintrc*", "dep:eslint"]),
            "type": ("npx tsc --noEmit", ["tsconfig.json"]),
            "format": ("npx prettier --check .", [".prettierrc*", "prettier.config.*", "dep:prettier"]),
        },
    },
    "javascript": {
        "label": "JavaScript", "manifests": ["package.json"],
        "exts": [".js", ".jsx", ".mjs", ".cjs"], "class_exts": ["js", "jsx", "mjs"],
        "src": ["src", "lib"], "tests": ["tests", "test", "__tests__", "__test__", "e2e"],
        "cmds": {
            "test": ("npx jest", ["jest.config.*", "dep:jest"]),
            "lint": ("npx eslint .", ["eslint.config.*", ".eslintrc*", "dep:eslint"]),
            "type": ("—", None),
            "format": ("npx prettier --check .", [".prettierrc*", "prettier.config.*", "dep:prettier"]),
        },
    },
    "go": {
        "label": "Go", "manifests": ["go.mod", "go.work"],
        "exts": [".go"], "class_exts": [],
        "src": ["internal", "cmd", "pkg"], "tests": [],  # tests are colocated *_test.go
        "cmds": {"test": ("go test ./...", None),
                 "lint": ("golangci-lint run", [".golangci.*"]),
                 "type": ("go vet ./...", None),
                 "format": ("gofmt -l . | (! grep .)", None)},
    },
    "rust": {
        "label": "Rust", "manifests": ["Cargo.toml"],
        "exts": [".rs"], "class_exts": [],
        "src": ["src", "crates"], "tests": ["tests", "benches"],
        "cmds": {"test": ("cargo test", None),
                 "lint": ("cargo clippy --all-targets -- -D warnings", None),
                 "type": ("cargo check --all-targets", None),
                 "format": ("cargo fmt --check", None)},
    },
    "java": {
        "label": "Java", "manifests": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "exts": [".java"], "class_exts": ["java"],
        "src": ["src/main/java"], "tests": ["src/test/java"],
        "cmds": {"test": ("{build} test", None),
                 "lint": ("{build} check", ["dep:checkstyle", "dep:spotbugs", "dep:pmd"]),
                 "type": ("{build} compile", None),
                 "format": ("{build} spotlessCheck", ["dep:spotless"])},
    },
    "kotlin": {
        "label": "Kotlin", "manifests": ["build.gradle.kts", "build.gradle"],
        "exts": [".kt", ".kts"], "class_exts": ["kt"],
        "src": ["src/main/kotlin"], "tests": ["src/test/kotlin"],
        "cmds": {"test": ("{build} test", None),
                 "lint": ("{build} detekt", ["dep:detekt"]),
                 "type": ("{build} compileKotlin", None),
                 "format": ("{build} ktlintCheck", ["dep:ktlint"])},
    },
    "csharp": {
        "label": "C#", "manifests": ["*.sln", "*.csproj"],
        "exts": [".cs"], "class_exts": ["cs"],
        "src": ["src"], "tests": ["tests", "test"],
        "cmds": {"test": ("dotnet test", None),
                 "lint": ("dotnet format --verify-no-changes --severity warn", None),
                 "type": ("dotnet build -warnaserror", None),
                 "format": ("dotnet format whitespace --verify-no-changes", None)},
    },
    "ruby": {
        "label": "Ruby", "manifests": ["Gemfile", "*.gemspec"],
        "exts": [".rb"], "class_exts": ["rb"],
        "src": ["app", "lib"], "tests": ["spec", "test"],
        "cmds": {"test": ("bundle exec rspec", [".rspec", "spec/spec_helper.rb", "dep:rspec"]),
                 "lint": ("bundle exec rubocop", [".rubocop.yml", "dep:rubocop"]),
                 "type": ("bundle exec srb tc", ["sorbet", "dep:sorbet"]),
                 "format": ("—", None)},
    },
    "php": {
        "label": "PHP", "manifests": ["composer.json"],
        "exts": [".php"], "class_exts": ["php"],
        "src": ["src", "app"], "tests": ["tests"],
        "cmds": {"test": ("vendor/bin/phpunit", ["phpunit.xml*", "dep:phpunit"]),
                 "lint": ("vendor/bin/phpcs", ["phpcs.xml*", "dep:squizlabs/php_codesniffer"]),
                 "type": ("vendor/bin/phpstan analyse", ["phpstan.neon*", "dep:phpstan"]),
                 "format": ("vendor/bin/php-cs-fixer fix --dry-run", [".php-cs-fixer*"])},
    },
    "elixir": {
        "label": "Elixir", "manifests": ["mix.exs"],
        "exts": [".ex", ".exs"], "class_exts": [],
        "src": ["lib"], "tests": ["test"],
        "cmds": {"test": ("mix test", None), "lint": ("mix credo --strict", ["dep:credo"]),
                 "type": ("mix dialyzer", ["dep:dialyxir"]),
                 "format": ("mix format --check-formatted", None)},
    },
    "swift": {
        "label": "Swift", "manifests": ["Package.swift"],
        "exts": [".swift"], "class_exts": ["swift"],
        "src": ["Sources"], "tests": ["Tests"],
        "cmds": {"test": ("swift test", None), "lint": ("swiftlint", [".swiftlint.yml"]),
                 "type": ("swift build", None), "format": ("swift-format lint -r .", [".swift-format"])},
    },
    "dart": {
        "label": "Dart", "manifests": ["pubspec.yaml"],
        "exts": [".dart"], "class_exts": ["dart"],
        "src": ["lib"], "tests": ["test"],
        "cmds": {"test": ("dart test", None), "lint": ("dart analyze", None),
                 "type": ("dart analyze", None),
                 "format": ("dart format --set-exit-if-changed .", None)},
    },
    "cpp": {
        "label": "C/C++", "manifests": ["CMakeLists.txt", "meson.build"],
        "exts": [".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"], "class_exts": ["cpp", "cc", "hpp", "h"],
        "src": ["src", "include"], "tests": ["tests", "test"],
        "cmds": {"test": ("ctest --test-dir build", ["CMakeLists.txt"]),
                 "lint": ("clang-tidy -p build", [".clang-tidy"]),
                 "type": ("cmake --build build", ["CMakeLists.txt"]),
                 "format": ("clang-format --dry-run --Werror", [".clang-format"])},
    },
    "sql": {
        # SQL-first projects (schema, functions, queries) have no conventional layout and rarely a
        # runner; roots come from the census and commands only from real evidence.
        "label": "SQL", "manifests": [".sqlfluff", "sqitch.plan", "flyway.conf", "liquibase.properties"],
        "exts": [".sql", ".psql", ".pgsql"], "class_exts": [],
        "src": [], "tests": ["test", "tests", "sql/test"],
        "cmds": {"test": ("pg_prove -r test/", ["dep:pgtap", "test/*.pg"]),
                 "lint": ("sqlfluff lint .", [".sqlfluff", "dep:sqlfluff"]),
                 "type": ("—", None),
                 "format": ("sqlfluff format --check .", [".sqlfluff"])},
    },
}
ALIASES = {"py": "python", "ts": "typescript", "js": "javascript", "node": "javascript",
           "golang": "go", "rs": "rust", "kt": "kotlin", "c#": "csharp", "cs": "csharp",
           "dotnet": "csharp", "rb": "ruby", "ex": "elixir", "c": "cpp", "c++": "cpp",
           "postgres": "sql", "plpgsql": "sql", "psql": "sql"}
# Manifest names too generic to prove their language on their own (a package.json for tooling,
# a pom.xml shared by Java/Kotlin, a CMakeLists.txt in a bindings dir).
WEAK_MANIFEST = {"javascript", "kotlin", "java", "cpp", "sql"}

# Directories the census never descends into: VCS, deps, build output, virtualenvs, and the
# template's own tooling so the scaffold itself never reads as "project code".
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "target", "build",
             "dist", "out", "vendor", ".next", ".nuxt", ".gradle", ".idea", ".vscode", ".claude",
             ".refmatrix", ".gmd", ".wolf", ".tldr", "tools", "docs", "workflow", "coverage",
             ".mypy_cache", ".pytest_cache", ".ruff_cache", "deps", "_build", "Pods", ".dart_tool",
             "cache", "tmp", "log", "logs"}
MAX_DEPTH = 6
TEST_DIR_RE = re.compile(r"^(__)?tests?(__)?$|(^|_)tests?($|_)|^specs?$|^e2e$|^testing$", re.I)
NOT_SRC_RE = re.compile(r"test|spec|e2e|fixture|sample|example|bench|demo|mock|^old|legacy|"
                        r"deprecated|^scratch", re.I)
UI_DIRS = ["ui", "frontend", "web", "client", "webapp", "app/frontend"]
STATIC_UI_DIRS = ["public", "static", "assets"]  # plain browser JS, no build step
MIGRATION_DIRS = ["alembic", "migrations", "db/migrate", "db/migrations", "prisma",
                  "src/main/resources/db/migration", "priv/repo/migrations"]
WORKSPACE_DIRS = ["packages", "apps", "services", "libs", "crates", "modules"]
DOC_EXTS = [".md", ".sh", ".json", ".yaml", ".yml", ".toml", ".txt"]

FRAMEWORKS = {  # manifest keyword -> display name
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask", "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic", "celery": "Celery", "react": "React", "next": "Next.js",
    "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular", "express": "Express",
    "@nestjs/core": "NestJS", "fastify": "Fastify", "vite": "Vite", "prisma": "Prisma",
    "gin-gonic/gin": "Gin", "labstack/echo": "Echo", "gofiber/fiber": "Fiber",
    "actix-web": "Actix Web", "axum": "Axum", "rocket": "Rocket", "tokio": "Tokio",
    "spring-boot": "Spring Boot", "ktor": "Ktor", "rails": "Rails", "sinatra": "Sinatra",
    "laravel/framework": "Laravel", "symfony/": "Symfony", "phoenix": "Phoenix",
    "Microsoft.AspNetCore": "ASP.NET Core", "flutter": "Flutter", "vapor": "Vapor",
}
DATABASES = {  # keyword (compose/manifest) -> display name
    "postgres": "PostgreSQL", "psycopg": "PostgreSQL", "asyncpg": "PostgreSQL", "\"pg\"": "PostgreSQL",
    "mysql": "MySQL", "mariadb": "MariaDB", "sqlite": "SQLite", "mongo": "MongoDB",
    "redis": "Redis", "elasticsearch": "Elasticsearch", "opensearch": "OpenSearch",
    "cassandra": "Cassandra", "dynamodb": "DynamoDB", "lancedb": "LanceDB", "duckdb": "DuckDB",
}
COMPOSE_FILES = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
MAKE_TARGETS = {"test": ["test"], "lint": ["lint"], "type": ["typecheck", "type-check", "types"],
                "format": ["format-check", "fmt-check", "check-format"]}


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------
def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s or "app"


def toml_load(p: Path) -> dict:
    if not p.is_file():
        return {}
    if tomllib is not None:
        try:
            return tomllib.loads(read(p))
        except Exception:
            return {}
    # Minimal fallback: pull name/description from the first matching table.
    out: dict = {}
    text = read(p)
    for table in ("project", "package", "tool.poetry"):
        m = re.search(rf"^\[{re.escape(table)}\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
        if m:
            body = m.group(1)
            d = {k: v for k, v in re.findall(r'^(name|description)\s*=\s*"([^"]*)"', body, re.M)}
            cur = out
            for part in table.split("."):
                cur = cur.setdefault(part, {})
            cur.update(d)
    return out


def skip_dir(parent: str, name: str) -> bool:
    return (name in SKIP_DIRS or name.startswith(".") or name.endswith(".egg-info")
            or os.path.isfile(os.path.join(parent, name, "pyvenv.cfg")))


def find_manifests(root: Path, pattern: str) -> list[Path]:
    """Manifests at the root and up to two levels down (monorepo members)."""
    hits: list[Path] = []
    for depth_glob in (pattern, f"*/{pattern}", f"*/*/{pattern}"):
        for p in root.glob(depth_glob):
            parts = p.relative_to(root).parts
            if not any(skip_dir(str(root.joinpath(*parts[:i])), parts[i])
                       for i in range(len(parts) - 1)):
                hits.append(p)
    return hits


def census(root: Path) -> tuple[Counter, dict[str, Counter], Counter]:
    """Count source files by extension — overall, per top-level dir, and at the repo root."""
    total: Counter = Counter()
    by_top: dict[str, Counter] = {}
    at_root: Counter = Counter()
    root_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).parts[root_depth:]
        dirnames[:] = [d for d in dirnames if not skip_dir(dirpath, d) and len(rel) < MAX_DEPTH]
        # scripts/ at the root carries the template's own tooling (sdd, lint-gmd, this file).
        if not rel and "scripts" in dirnames and (root / "scripts/sdd").is_dir():
            dirnames.remove("scripts")
        for f in filenames:
            ext = Path(f).suffix.lower()
            total[ext] += 1
            if rel:
                by_top.setdefault(rel[0], Counter())[ext] += 1
            else:
                at_root[ext] += 1
    return total, by_top, at_root


def has_src_files(root: Path, rel: str, exts: list[str]) -> bool:
    d = root / rel
    if not d.is_dir():
        return False
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames if not skip_dir(dirpath, x)]
        if any(Path(f).suffix.lower() in exts for f in filenames):
            return True
    return False


def make_targets(root: Path) -> set[str]:
    text = read(root / "Makefile") or read(root / "makefile")
    return set(re.findall(r"^([A-Za-z][\w-]*)\s*:(?!=)", text, re.M))


# --------------------------------------------------------------------------------------------
# detection
# --------------------------------------------------------------------------------------------
def detect(root: Path) -> dict:
    total, by_top, at_root = census(root)
    manifests: dict[str, list[str]] = {}
    for key, spec in LANGS.items():
        for pat in spec["manifests"]:
            for p in find_manifests(root, pat):
                manifests.setdefault(key, []).append(str(p.relative_to(root)))

    # A language counts when it carries a real share of the source (>= 3 files and >= 5% of
    # all source), or its own non-generic manifest is at the root. Smaller traces are reported
    # as "also present" but do not shape layout, commands, or the corpus.
    counts = {k: sum(total[e] for e in s["exts"]) for k, s in LANGS.items()}
    all_src = sum(counts.values()) or 1
    langs, minor = [], []
    for key in LANGS:
        n = counts[key]
        root_manifest = any("/" not in m for m in manifests.get(key, []))
        if (n >= 3 and n / all_src >= 0.05) or (root_manifest and key not in WEAK_MANIFEST):
            langs.append(key)
        elif n:
            minor.append(key)
    if "java" in langs and "kotlin" in langs and counts["kotlin"] < counts["java"] / 10:
        langs.remove("kotlin")
    # TypeScript subsumes the JavaScript toolchain when it dominates.
    if "typescript" in langs and "javascript" in langs and counts["javascript"] < counts["typescript"]:
        langs.remove("javascript")
    langs.sort(key=lambda k: -counts[k])

    info: dict = {"langs": langs, "counts": counts, "minor": minor, "manifests": manifests,
                  "greenfield": not langs}

    # identity from manifests
    name = desc = ""
    py = toml_load(root / "pyproject.toml")
    proj = (py.get("project") or py.get("tool", {}).get("poetry", {})) if py else {}
    if proj:
        name, desc = proj.get("name", ""), proj.get("description", "")
    setup_py = read(root / "setup.py")
    if not name and setup_py:
        m = re.search(r"name\s*=\s*['\"]([^'\"]+)", setup_py)
        name = m.group(1) if m else ""
        m = re.search(r"description\s*=\s*['\"]([^'\"]+)", setup_py)
        desc = desc or (m.group(1) if m else "")
    pkgjson: dict = {}
    if (root / "package.json").is_file():
        try:
            pkgjson = json.loads(read(root / "package.json"))
        except ValueError:
            pkgjson = {}
        name = name or str(pkgjson.get("name", "")).split("/")[-1]
        desc = desc or str(pkgjson.get("description", ""))
    cargo = toml_load(root / "Cargo.toml").get("package", {})
    name, desc = name or cargo.get("name", ""), desc or cargo.get("description", "")
    m = re.search(r"^module\s+(\S+)", read(root / "go.mod"), re.M)
    if m:
        name = name or m.group(1).rstrip("/").split("/")[-1]
    info["name"], info["description"] = name, desc

    # package / module name — Python needs the importable package dir
    pkg = ""
    if "python" in langs:
        for base in (root / "src", root):
            if not base.is_dir():
                continue
            for d in sorted(base.iterdir()):
                if d.is_dir() and (d / "__init__.py").is_file() and not skip_dir(str(base), d.name) \
                        and not NOT_SRC_RE.search(d.name) and d.name != "scripts":
                    pkg = d.name
                    break
            if pkg:
                break
    info["package"] = pkg or (slug(name) if name else "")

    # ---- layout: conventional roots first, then whatever top-level dirs actually hold source
    exts = [e for k in langs for e in LANGS[k]["exts"]]
    tests: list[str] = []
    for d in sorted(by_top):
        if TEST_DIR_RE.search(d) and (root / d).is_dir():
            tests.append(d)
    for key in langs:
        for cand in LANGS[key]["tests"]:
            if (root / cand).is_dir() and cand not in tests:
                tests.append(cand)
    ui = next((d for d in UI_DIRS if (root / d).is_dir()
               and ((root / d / "package.json").is_file()
                    or has_src_files(root, d, [".tsx", ".jsx", ".vue", ".svelte"]))), "")
    if not ui:
        ui = next((d for d in STATIC_UI_DIRS
                   if sum(by_top.get(d, Counter())[e] for e in (".js", ".ts", ".jsx", ".tsx")) >= 3), "")
    migrations = [d for d in MIGRATION_DIRS if (root / d).is_dir()]

    src: list[str] = []
    for key in langs:
        for cand in LANGS[key]["src"]:
            rel = cand.format(pkg=info["package"] or "\0")
            if has_src_files(root, rel, LANGS[key]["exts"]) and rel not in src:
                src.append(rel)
                if key != "go":  # Go legitimately uses cmd/ + internal/ + pkg/ together
                    break
    covered = {s.split("/")[0] for s in src}
    extra = sorted(((sum(c[e] for e in exts), d) for d, c in by_top.items()
                    if d not in covered and d not in tests and d != ui and d not in migrations
                    and not NOT_SRC_RE.search(d) and (root / d).is_dir()), reverse=True)
    src += [d for n, d in extra if n > 0]

    ws_markers = [f for f in ("pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json",
                              "go.work", "rush.json") if (root / f).is_file()]
    if pkgjson.get("workspaces"):
        ws_markers.append("package.json#workspaces")
    if "workspace" in toml_load(root / "Cargo.toml"):
        ws_markers.append("Cargo.toml#workspace")
    if py and "workspace" in py.get("tool", {}).get("uv", {}):
        ws_markers.append("pyproject.toml#tool.uv.workspace")
    info["monorepo"] = bool(ws_markers)
    info["workspace_markers"] = ws_markers
    if info["monorepo"]:
        src += [d for d in WORKSPACE_DIRS if (root / d).is_dir() and d not in src]
    info.update(src_roots=src, test_roots=tests, ui=ui, migrations=migrations)
    info["root_sources"] = sum(at_root[e] for e in exts)
    info["compose"] = next((f for f in COMPOSE_FILES if (root / f).is_file()), "")
    info["dockerfile"] = (root / "Dockerfile").is_file() or any(root.glob("docker/Dockerfile*"))

    # frameworks + databases from manifest/compose text
    blob = "\n".join(read(root / p) for ps in manifests.values() for p in ps).lower()
    info["manifest_blob"] = blob
    info["frameworks"] = sorted({v for k, v in FRAMEWORKS.items()
                                 if re.search(rf"[\"'/\s=@]{re.escape(k.lower())}[\"'\s=<>~^@,\]]", blob)})
    db_blob = blob + "\n" + (read(root / info["compose"]).lower() if info["compose"] else "")
    info["databases"] = sorted({v for k, v in DATABASES.items() if k in db_blob})

    scripts = pkgjson.get("scripts")
    if not isinstance(scripts, dict):
        scripts = {}
    info["npm_scripts"] = {"test": "npm test"} if "test" in scripts else {}
    for want, names in (("lint", ["lint"]), ("type", ["typecheck", "type-check", "tsc"]),
                        ("format", ["format:check", "prettier:check", "fmt:check"])):
        hit = next((n for n in names if n in scripts), None)
        if hit:
            info["npm_scripts"][want] = f"npm run {hit}"
    targets = make_targets(root)
    info["make"] = {k: f"make {next(t for t in v if t in targets)}"
                    for k, v in MAKE_TARGETS.items() if any(t in targets for t in v)}
    info["build_tool"] = "./gradlew" if (root / "gradlew").is_file() else (
        "gradle" if any(root.glob("build.gradle*")) else ("mvn" if (root / "pom.xml").is_file() else ""))
    return info


def has_evidence(root: Path, blob: str, markers: list[str] | None) -> bool:
    if markers is None:
        return True
    for m in markers:
        if m.startswith("dep:"):
            if re.search(rf"(^|[^a-z0-9_-]){re.escape(m[4:].lower())}([^a-z0-9_-]|$)", blob, re.M):
                return True
        elif any(root.glob(m)):
            return True
    for cfg in PY_CFG:  # [tool.<x>] tables in Python config files
        text = read(root / cfg)
        for m in markers:
            if m.startswith("dep:") and (f"[tool.{m[4:]}" in text or f"[{m[4:]}]" in text):
                return True
    return False


# --------------------------------------------------------------------------------------------
# prompting (from-scratch projects)
# --------------------------------------------------------------------------------------------
class Prompter:
    def __init__(self, enabled: bool) -> None:
        self.tty = None
        if enabled:
            try:
                self.tty = sys.stdin if sys.stdin.isatty() else open("/dev/tty", "r+")
            except OSError:
                self.tty = None

    @property
    def interactive(self) -> bool:
        return self.tty is not None

    def ask(self, q: str, default: str = "") -> str:
        if not self.tty:
            return default
        suffix = f" [{default}]" if default else ""
        sys.stderr.write(f"  ? {q}{suffix}: ")
        sys.stderr.flush()
        ans = self.tty.readline()
        if not ans:  # EOF
            return default
        return ans.strip() or default


def norm_langs(raw: str) -> list[str]:
    out = []
    for tok in re.split(r"[,\s]+", raw.strip().lower()):
        if not tok:
            continue
        key = ALIASES.get(tok, tok)
        if key not in LANGS:
            sys.stderr.write(f"  !! unknown language '{tok}' — known: {', '.join(LANGS)}\n")
            continue
        if key not in out:
            out.append(key)
    return out


def greenfield_questions(info: dict, args: argparse.Namespace, pr: Prompter, root: Path) -> None:
    sys.stderr.write("\n  No code or language manifests found — this looks like a from-scratch "
                     "project.\n  Answer a few questions so the scaffold is tuned to it "
                     "(Enter accepts the default).\n\n")
    info["name"] = args.name or pr.ask("Project name", info.get("name") or root.name)
    info["description"] = args.description or pr.ask("One-line description", info.get("description", ""))
    langs = norm_langs(args.lang) if args.lang else []
    while not langs:
        langs = norm_langs(pr.ask(f"Language(s), primary first ({' '.join(LANGS)})", "python"))
    info["langs"] = langs
    info["package"] = args.package or pr.ask("Package / module name", slug(info["name"]))
    hint = {"python": "e.g. FastAPI", "typescript": "e.g. React, Express", "go": "e.g. Gin",
            "rust": "e.g. Axum", "java": "e.g. Spring Boot", "ruby": "e.g. Rails",
            "sql": "e.g. pgTAP, sqitch"}
    fw = pr.ask(f"Frameworks ({hint.get(langs[0], 'comma-separated')}; blank for none)", "")
    info["frameworks"] = [f.strip() for f in fw.split(",") if f.strip()]
    db = args.db or pr.ask("Database (postgres, mysql, sqlite, mongodb, none)", "none")
    info["databases"] = [] if db.lower() in ("", "none", "-") else [
        DATABASES.get(db.lower(), DATABASES.get(db.lower().rstrip("ql"), db))]
    ui = args.ui if args.ui is not None else pr.ask("Frontend/UI directory (blank for none)", "")
    info["ui"] = ui.strip().strip("/")
    info["os"] = args.os or pr.ask("Target OS", "Ubuntu 24.04")
    # conventional layout for the chosen language(s)
    src, tests = [], []
    for key in langs:
        spec = LANGS[key]
        if key == "go":
            src += [d for d in ("cmd", "internal") if d not in src]
        elif key == "sql":
            src += [d for d in ("schema", "functions") if d not in src]
        elif spec["src"][0].format(pkg=info["package"]) not in src:
            src.append(spec["src"][0].format(pkg=info["package"]))
        if spec["tests"] and spec["tests"][0] not in tests:
            tests.append(spec["tests"][0])
    info["src_roots"], info["test_roots"] = src, tests
    info["migrations"] = ["alembic"] if info["databases"] and langs[0] == "python" \
        else (["migrations"] if info["databases"] else [])
    if args.skeleton is None:
        dirs = src + tests + ([info["ui"]] if info["ui"] else []) + info["migrations"]
        args.skeleton = pr.ask(f"Create the directory skeleton ({', '.join(dirs)})? [Y/n]",
                               "y").lower().startswith("y")


# --------------------------------------------------------------------------------------------
# derivation: commands, corpus, hooks.env
# --------------------------------------------------------------------------------------------
def commands(info: dict, root: Path) -> dict[str, str]:
    """Commands the project has evidence for. Greenfield: the idiomatic set, all *proposed*."""
    if not info["langs"]:
        return {}
    primary = info["langs"][0]
    venv_py = f"/opt/{info['package'] or '{project_package}'}-venv/bin/python" \
        if info.get("compose") or info["greenfield"] else "python3"
    fmt = {"py": venv_py, "src": info["src_roots"][0] if info["src_roots"] else ".",
           "build": info.get("build_tool") or "./gradlew"}
    blob = info.get("manifest_blob", "")
    out: dict[str, str] = {}
    for kind, (cmd, markers) in LANGS[primary]["cmds"].items():
        if cmd == "—":
            continue
        if info["greenfield"] or has_evidence(root, blob, markers):
            out[kind] = cmd.format(**fmt)
    # What the project itself declares wins over idioms.
    if primary in ("javascript", "typescript"):
        out.update(info.get("npm_scripts", {}))
    out.update(info.get("make", {}))
    return out


def fmt_cmd(cmd: str, log: str, info: dict) -> str:
    if not cmd:
        return "— (none detected — do not invent one)" if not info["greenfield"] else "—"
    if info["greenfield"]:
        return f"`{cmd}` *(proposed — toolchain not set up yet)*"
    if info.get("compose"):
        return f'`docker compose exec dev bash -c "{cmd} 2>&1 | tee /test-output/{log}.log"`'
    return f"`{cmd}`"


def corpus(info: dict) -> tuple[list[str], list[str]]:
    roots: list[str] = []
    for d in info["src_roots"] + info["test_roots"] + ([info["ui"]] if info["ui"] else []) \
            + info["migrations"] + ["docs", "workflow"]:
        top = d if info["monorepo"] else d.split("/")[0]
        if top and top not in roots:
            roots.append(top)
    exts: list[str] = []
    for key in info["langs"]:
        exts += [e for e in LANGS[key]["exts"] if e not in exts]
    if info["ui"]:
        exts += [e for e in (".ts", ".tsx", ".js", ".jsx", ".css", ".html") if e not in exts]
    exts += [e for e in DOC_EXTS if e not in exts]
    return roots, exts


def hooks_env(info: dict) -> str:
    roots, exts = corpus(info)
    class_exts: list[str] = []
    for key in info["langs"]:
        class_exts += [e for e in LANGS[key]["class_exts"] if e not in class_exts]
    # No class-bearing language (Go, Rust, Elixir, SQL) -> a never-matching regex keeps the gate inert.
    gate_re = f"\\.({'|'.join(class_exts)})$" if class_exts else "^$"
    langs = ", ".join(LANGS[k]["label"] for k in info["langs"]) or "no language detected"
    return f"""# Hook configuration — generated by scripts/tune-project.py from the detected project layout
# ({langs}). Regenerated on re-run while untouched; edit freely — edits are preserved.
# Values mirror .claude/PROJECT_PROFILE.md (Directory layout + Discovery corpus).

# Source root(s) the adr-gate scans for new class definitions (space-separated, repo-relative).
SRC_DIR="{' '.join(info['src_roots']) or 'src'}"

# Where ADRs live (adr-gate greps these for class-name matches).
ADR_DIR="docs/architecture/adr"

# Space-separated corpus roots. Bare grep into these is redirected to rmx by enforce-rmx-grep.
CORPUS_PATHS="{' '.join(roots)}"

# Source-file extensions considered "corpus" content.
CORPUS_EXTS="{' '.join(exts)}"

# File-glob (extended regex) adr-gate inspects for new class defs (class-bearing languages only).
ADR_GATE_FILE_RE='{gate_re}'
"""


# --------------------------------------------------------------------------------------------
# PROJECT_PROFILE.md
# --------------------------------------------------------------------------------------------
# Template-shipped values that are defaults rather than project facts — replaceable like `{…}`.
PRISTINE = {
    "UI (if any)": "`ui/`",
    "Source extensions": "`.py .ts .tsx .js .md .sh .json .yaml .toml`",
}
FIELD_RE = re.compile(r"^- \*\*([^*]+):\*\* (.*)$", re.M)
DETECT_BEGIN = "<!-- tune-project:begin (generated — re-run scripts/tune-project.py) -->"
DETECT_END = "<!-- tune-project:end -->"


def untouched(key: str, value: str) -> bool:
    return "{" in value or "…" in value or PRISTINE.get(key) == value


def profile_is_tuned(text: str) -> bool:
    """A profile whose identity + stack were filled (by a person or a previous run) is
    project-owned. Hand-tuned profiles may rename fields (e.g. `Language:`), so a missing
    field counts as filled; only a surviving placeholder counts as untuned."""
    fields = dict(FIELD_RE.findall(text))
    if "Name" not in fields or untouched("Name", fields["Name"]):
        return False
    return not any(untouched(k, fields[k]) for k in ("Language(s)", "Language") if k in fields)


def fill_profile(text: str, info: dict, cmds: dict[str, str]) -> tuple[str, list[str]]:
    roots, exts = corpus(info)
    pkg = info["package"]
    python_first = info["langs"][:1] == ["python"]
    logs = ("pytest", "ruff", "mypy", "black") if python_first else ("test", "lint", "typecheck", "format")
    values = {
        "Name": info.get("name", ""),
        "One-liner": info.get("description", ""),
        "Package / module": pkg,
        "Language(s)": ", ".join(LANGS[k]["label"] for k in info["langs"]),
        "Frameworks": ", ".join(info.get("frameworks", [])),
        "Storage": ", ".join(info.get("databases", [])),
        "Target OS": info.get("os", ""),
        "Source root": ", ".join(f"`{d}/`" for d in info["src_roots"]),
        "Tests": ", ".join(f"`{d}/`" for d in info["test_roots"])
                 or ("colocated (`*_test.go`)" if info["langs"][:1] == ["go"] else "none found"),
        "UI (if any)": f"`{info['ui']}/`" if info["ui"] else "—",
        "Migrations/schema": ", ".join(f"`{d}/`" for d in info["migrations"]) or "—",
        "Test": fmt_cmd(cmds.get("test", ""), logs[0], info),
        "Lint": fmt_cmd(cmds.get("lint", ""), logs[1], info),
        "Type check": fmt_cmd(cmds.get("type", ""), logs[2], info),
        "Format check": fmt_cmd(cmds.get("format", ""), logs[3], info),
        "UI tests (if any)": "—",
        "Corpus roots": "`" + " ".join(roots) + "`",
        "Source extensions": "`" + " ".join(exts) + "`",
    }
    filled: list[str] = []

    def sub(m: re.Match) -> str:
        key, cur = m.group(1), m.group(2)
        new = values.get(key, "")
        if not untouched(key, cur) or not new:  # never overwrite a project-authored value
            return m.group(0)
        filled.append(key)
        return f"- **{key}:** {new}"

    text = FIELD_RE.sub(sub, text)
    if python_first and pkg and info.get("compose"):
        text = text.replace("/opt/{project_package}-venv", f"/opt/{pkg}-venv")
    elif not info["greenfield"] and not info.get("compose"):
        text = re.sub(r"^All commands run in Docker \(see CLAUDE\.md\)\. The venv is at .*$",
                      "No docker compose file was found, so these run on the host as detected. "
                      "Either set up Docker (SETUP.md) or adapt CLAUDE.md's Docker-only rule.",
                      text, flags=re.M)
    elif not python_first:
        text = re.sub(r"^All commands run in Docker \(see CLAUDE\.md\)\. The venv is at .*$",
                      "All commands run in Docker (see CLAUDE.md) via `docker compose exec dev`.",
                      text, flags=re.M)

    # Evidence section — replaced wholesale on every run.
    ev = [DETECT_BEGIN, "", "## Install detection {#install-detection}", ""]
    counts = info["counts"]
    if info["greenfield"]:
        ev.append("- **Mode:** from scratch — values above came from install-time answers; "
                  "commands are proposals until the toolchain exists")
    else:
        ev.append("- **Mode:** existing codebase — values above were detected; a command shown as "
                  "none has no config/dependency/script evidence")
        ev.append("- **Source files:** " + ", ".join(
            f"{LANGS[k]['label']} {counts[k]}" for k in info["langs"]))
        if info["minor"]:
            ev.append("- **Also present (minor, not tuned for):** " + ", ".join(
                f"{LANGS[k]['label']} {counts[k]}" for k in info["minor"]))
        ev.append("- **Manifests:** " + (", ".join(
            f"`{p}`" for ps in info["manifests"].values() for p in ps[:4]) or "—"))
        if info["root_sources"]:
            ev.append(f"- **Repo-root sources:** {info['root_sources']} file(s) at the top level "
                      "(not expressible as a SRC_DIR root)")
    if info.get("monorepo"):
        ev.append("- **Monorepo:** " + ", ".join(f"`{m}`" for m in info["workspace_markers"]))
    docker = [f"`{info['compose']}`"] if info.get("compose") else []
    docker += ["Dockerfile"] if info.get("dockerfile") else []
    ev.append("- **Docker:** " + (", ".join(docker) or "none — CLAUDE.md assumes Docker; adapt it "
                                  "or set Docker up (SETUP.md)"))
    ev += ["", "Detection is a starting point: confirm every value, then finish the tuning steps in",
           "`docs/ONBOARDING.md` (placeholders in CLAUDE.md, stack-specific Development Commands,",
           "Docker setup, agent overlays, constitution).", "", DETECT_END]
    block = "\n".join(ev)
    if DETECT_BEGIN in text:
        text = re.sub(re.escape(DETECT_BEGIN) + r".*?" + re.escape(DETECT_END), lambda _: block,
                      text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    return text, filled


# --------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Tune the cat-herder scaffold to this project.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--name")
    ap.add_argument("--description")
    ap.add_argument("--lang", help="comma-separated languages, primary first (e.g. python,ts)")
    ap.add_argument("--package")
    ap.add_argument("--db")
    ap.add_argument("--ui")
    ap.add_argument("--os")
    ap.add_argument("--no-prompt", action="store_true", help="never prompt; use flags + detection")
    ap.add_argument("--skeleton", dest="skeleton", action="store_true", default=None)
    ap.add_argument("--no-skeleton", dest="skeleton", action="store_false")
    ap.add_argument("--dry-run", action="store_true", help="report + print hooks.env; write nothing")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    say = lambda s: sys.stderr.write(f"  {s}\n")  # noqa: E731
    prof_p = root / ".claude/PROJECT_PROFILE.md"
    tuned = prof_p.is_file() and profile_is_tuned(read(prof_p))
    info = detect(root)
    pr = Prompter(enabled=not (args.no_prompt or args.dry_run or tuned))

    if tuned:
        say("PROJECT_PROFILE.md is already tuned (project-owned) — reporting detection only")
    elif info["greenfield"]:
        if not pr.interactive and not args.lang:
            say("!! from-scratch project and no terminal to prompt on. Re-run interactively "
                "(python3 scripts/tune-project.py) or pass --lang=… [--name= --package= --db= --ui=]. "
                "Nothing tuned.")
            return 0
        greenfield_questions(info, args, pr, root)
    else:
        # Flags override detection; prompts only fill identity gaps detection could not.
        if args.lang:
            info["langs"] = norm_langs(args.lang) or info["langs"]
        info["name"] = args.name or info["name"] or pr.ask("Project name", root.name)
        info["description"] = args.description or info["description"] or pr.ask(
            "One-line description (blank to fill later)", "")
        info["package"] = args.package or info["package"] or slug(info["name"])
        if args.db:
            info["databases"] = [args.db]
        if args.ui is not None:
            info["ui"] = args.ui.strip("/")
        info["os"] = args.os or ""

    cmds = commands(info, root)
    say(f"languages: {', '.join(LANGS[k]['label'] for k in info['langs']) or '—'}"
        + (" (monorepo)" if info.get("monorepo") else "")
        + (f"   minor: {', '.join(LANGS[k]['label'] for k in info['minor'])}" if info.get("minor") else ""))
    say(f"source:    {' '.join(info['src_roots']) or '—'}")
    say(f"tests:     {' '.join(info['test_roots']) or '—'}   ui: {info['ui'] or '—'}"
        f"   migrations: {' '.join(info['migrations']) or '—'}"
        f"   docker: {info.get('compose') or ('Dockerfile' if info.get('dockerfile') else '—')}")
    if info.get("frameworks"):
        say(f"frameworks: {', '.join(info['frameworks'])}")
    if info.get("databases"):
        say(f"storage:   {', '.join(info['databases'])}")
    for k in ("test", "lint", "type", "format"):
        say(f"{k + ':':<10} {cmds.get(k, '— (no evidence)')}"
            + (" (proposed)" if info["greenfield"] and cmds.get(k) else ""))

    if args.dry_run:
        sys.stdout.write(hooks_env(info))
        return 0

    # hooks.env — generate when absent or still the untouched example.
    env_p, ex_p = root / ".claude/hooks/hooks.env", root / ".claude/hooks/hooks.env.example"
    if not env_p.exists() or (ex_p.exists() and read(env_p) == read(ex_p)):
        env_p.parent.mkdir(parents=True, exist_ok=True)
        env_p.write_text(hooks_env(info), encoding="utf-8")
        say("wrote .claude/hooks/hooks.env (tuned to detected layout)")
    else:
        say(".claude/hooks/hooks.env preserved (project-edited) — detected: "
            f"SRC_DIR=\"{' '.join(info['src_roots'])}\" CORPUS_PATHS=\"{' '.join(corpus(info)[0])}\"")

    if prof_p.is_file() and not tuned:
        text, filled = fill_profile(read(prof_p), info, cmds)
        prof_p.write_text(text, encoding="utf-8")
        say(f"filled PROJECT_PROFILE.md: {', '.join(filled) or 'nothing left to fill'}")
        left = [k for k, v in FIELD_RE.findall(text) if untouched(k, v)]
        if left:
            say(f"still to fill by hand: {', '.join(left)}")

    if info["greenfield"] and args.skeleton:
        for d in info["src_roots"] + info["test_roots"] + ([info["ui"]] if info["ui"] else []) \
                + info["migrations"]:
            p = root / d
            if not p.exists():
                p.mkdir(parents=True)
                (p / ".gitkeep").touch()
                say(f"created {d}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
