#!/usr/bin/env python3
"""tune-project.py — tune a cat-herder scaffold to the project it was installed into.

Tuning is part of install: ./install.sh runs this after scaffolding. It can also be re-run by
hand at any time (e.g. after the codebase grows a new language or directory).

EXISTING project  -> detects languages (manifests + source-file census), the directory layout
                     actually in use (conventional per-language roots AND non-conventional
                     top-level dirs holding source), test/ui/migration roots, monorepo
                     workspaces, frameworks, database, Docker, and the test/lint/type-check/format
                     commands the project has EVIDENCE for (config files, dependencies,
                     package.json scripts, Makefile targets). A command with no evidence is
                     written as "— (none detected)" rather than invented.
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
import hashlib
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
        "label": "Python",
        "manifests": ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"],
        "exts": [".py"],
        "class_exts": ["py"],
        "src": ["src/{pkg}", "{pkg}", "src"],
        "tests": ["tests", "test"],
        "cmds": {
            "test": (
                "{py} -m pytest -v",
                [
                    "pytest.ini",
                    "conftest.py",
                    "tests/conftest.py",
                    "tests/test_*.py",
                    "test/test_*.py",
                    "dep:pytest",
                ],
            ),
            "lint": ("{py} -m ruff check .", ["ruff.toml", ".ruff.toml", "dep:ruff"]),
            "type": ("{py} -m mypy {src}", ["mypy.ini", ".mypy.ini", "dep:mypy"]),
            "format": ("{py} -m black --check . --line-length 100", ["dep:black"]),
        },
    },
    "typescript": {
        "label": "TypeScript",
        "manifests": ["tsconfig.json"],
        "exts": [".ts", ".tsx"],
        "class_exts": ["ts", "tsx"],
        "src": ["src"],
        "tests": ["tests", "test", "__tests__", "e2e"],
        "cmds": {
            "test": ("npx vitest run", ["vitest.config.*", "dep:vitest"]),
            "lint": ("npx eslint .", ["eslint.config.*", ".eslintrc*", "dep:eslint"]),
            "type": ("npx tsc --noEmit", ["tsconfig.json"]),
            "format": (
                "npx prettier --check .",
                [".prettierrc*", "prettier.config.*", "dep:prettier"],
            ),
        },
    },
    "javascript": {
        "label": "JavaScript",
        "manifests": ["package.json"],
        "exts": [".js", ".jsx", ".mjs", ".cjs"],
        "class_exts": ["js", "jsx", "mjs"],
        "src": ["src", "lib"],
        "tests": ["tests", "test", "__tests__", "__test__", "e2e"],
        "cmds": {
            "test": ("npx jest", ["jest.config.*", "dep:jest"]),
            "lint": ("npx eslint .", ["eslint.config.*", ".eslintrc*", "dep:eslint"]),
            "type": ("—", None),
            "format": (
                "npx prettier --check .",
                [".prettierrc*", "prettier.config.*", "dep:prettier"],
            ),
        },
    },
    "go": {
        "label": "Go",
        "manifests": ["go.mod", "go.work"],
        "exts": [".go"],
        "class_exts": [],
        "src": ["internal", "cmd", "pkg"],
        "tests": [],  # tests are colocated *_test.go
        "cmds": {
            "test": ("go test ./...", None),
            "lint": ("golangci-lint run", [".golangci.*"]),
            "type": ("go vet ./...", None),
            "format": ("gofmt -l . | (! grep .)", None),
        },
    },
    "rust": {
        "label": "Rust",
        "manifests": ["Cargo.toml"],
        "exts": [".rs"],
        "class_exts": [],
        "src": ["src", "crates"],
        "tests": ["tests", "benches"],
        "cmds": {
            "test": ("cargo test", None),
            "lint": ("cargo clippy --all-targets -- -D warnings", None),
            "type": ("cargo check --all-targets", None),
            "format": ("cargo fmt --check", None),
        },
    },
    "java": {
        "label": "Java",
        "manifests": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "exts": [".java"],
        "class_exts": ["java"],
        "src": ["src/main/java"],
        "tests": ["src/test/java"],
        "cmds": {
            "test": ("{build} test", None),
            "lint": ("{build} check", ["dep:checkstyle", "dep:spotbugs", "dep:pmd"]),
            "type": ("{build} compile", None),
            "format": ("{build} spotlessCheck", ["dep:spotless"]),
        },
    },
    "kotlin": {
        "label": "Kotlin",
        "manifests": ["build.gradle.kts", "build.gradle"],
        "exts": [".kt", ".kts"],
        "class_exts": ["kt"],
        "src": ["src/main/kotlin"],
        "tests": ["src/test/kotlin"],
        "cmds": {
            "test": ("{build} test", None),
            "lint": ("{build} detekt", ["dep:detekt"]),
            "type": ("{build} compileKotlin", None),
            "format": ("{build} ktlintCheck", ["dep:ktlint"]),
        },
    },
    "csharp": {
        "label": "C#",
        "manifests": ["*.sln", "*.csproj"],
        "exts": [".cs"],
        "class_exts": ["cs"],
        "src": ["src"],
        "tests": ["tests", "test"],
        "cmds": {
            "test": ("dotnet test", None),
            "lint": ("dotnet format --verify-no-changes --severity warn", None),
            "type": ("dotnet build -warnaserror", None),
            "format": ("dotnet format whitespace --verify-no-changes", None),
        },
    },
    "ruby": {
        "label": "Ruby",
        "manifests": ["Gemfile", "*.gemspec"],
        "exts": [".rb"],
        "class_exts": ["rb"],
        "src": ["app", "lib"],
        "tests": ["spec", "test"],
        "cmds": {
            "test": ("bundle exec rspec", [".rspec", "spec/spec_helper.rb", "dep:rspec"]),
            "lint": ("bundle exec rubocop", [".rubocop.yml", "dep:rubocop"]),
            "type": ("bundle exec srb tc", ["sorbet", "dep:sorbet"]),
            "format": ("—", None),
        },
    },
    "php": {
        "label": "PHP",
        "manifests": ["composer.json"],
        "exts": [".php"],
        "class_exts": ["php"],
        "src": ["src", "app"],
        "tests": ["tests"],
        "cmds": {
            "test": ("vendor/bin/phpunit", ["phpunit.xml*", "dep:phpunit"]),
            "lint": ("vendor/bin/phpcs", ["phpcs.xml*", "dep:squizlabs/php_codesniffer"]),
            "type": ("vendor/bin/phpstan analyse", ["phpstan.neon*", "dep:phpstan"]),
            "format": ("vendor/bin/php-cs-fixer fix --dry-run", [".php-cs-fixer*"]),
        },
    },
    "elixir": {
        "label": "Elixir",
        "manifests": ["mix.exs"],
        "exts": [".ex", ".exs"],
        "class_exts": [],
        "src": ["lib"],
        "tests": ["test"],
        "cmds": {
            "test": ("mix test", None),
            "lint": ("mix credo --strict", ["dep:credo"]),
            "type": ("mix dialyzer", ["dep:dialyxir"]),
            "format": ("mix format --check-formatted", None),
        },
    },
    "swift": {
        "label": "Swift",
        "manifests": ["Package.swift"],
        "exts": [".swift"],
        "class_exts": ["swift"],
        "src": ["Sources"],
        "tests": ["Tests"],
        "cmds": {
            "test": ("swift test", None),
            "lint": ("swiftlint", [".swiftlint.yml"]),
            "type": ("swift build", None),
            "format": ("swift-format lint -r .", [".swift-format"]),
        },
    },
    "dart": {
        "label": "Dart",
        "manifests": ["pubspec.yaml"],
        "exts": [".dart"],
        "class_exts": ["dart"],
        "src": ["lib"],
        "tests": ["test"],
        "cmds": {
            "test": ("dart test", None),
            "lint": ("dart analyze", None),
            "type": ("dart analyze", None),
            "format": ("dart format --set-exit-if-changed .", None),
        },
    },
    "cpp": {
        "label": "C/C++",
        "manifests": ["CMakeLists.txt", "meson.build"],
        "exts": [".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"],
        "class_exts": ["cpp", "cc", "hpp", "h"],
        "src": ["src", "include"],
        "tests": ["tests", "test"],
        "cmds": {
            "test": ("ctest --test-dir build", ["CMakeLists.txt"]),
            "lint": ("clang-tidy -p build", [".clang-tidy"]),
            "type": ("cmake --build build", ["CMakeLists.txt"]),
            "format": ("clang-format --dry-run --Werror", [".clang-format"]),
        },
    },
    "sql": {
        # SQL-first projects (schema, functions, queries) have no conventional layout and rarely a
        # runner; roots come from the census and commands only from real evidence.
        "label": "SQL",
        "manifests": [".sqlfluff", "sqitch.plan", "flyway.conf", "liquibase.properties"],
        "exts": [".sql", ".psql", ".pgsql"],
        "class_exts": [],
        "src": [],
        "tests": ["test", "tests", "sql/test"],
        "cmds": {
            "test": ("pg_prove -r test/", ["dep:pgtap", "test/*.pg"]),
            "lint": ("sqlfluff lint .", [".sqlfluff", "dep:sqlfluff"]),
            "type": ("—", None),
            "format": ("sqlfluff format --check .", [".sqlfluff"]),
        },
    },
}
ALIASES = {
    "py": "python",
    "ts": "typescript",
    "js": "javascript",
    "node": "javascript",
    "golang": "go",
    "rs": "rust",
    "kt": "kotlin",
    "c#": "csharp",
    "cs": "csharp",
    "dotnet": "csharp",
    "rb": "ruby",
    "ex": "elixir",
    "c": "cpp",
    "c++": "cpp",
    "postgres": "sql",
    "plpgsql": "sql",
    "psql": "sql",
}
# Manifest names too generic to prove their language on their own (a package.json for tooling,
# a pom.xml shared by Java/Kotlin, a CMakeLists.txt in a bindings dir).
WEAK_MANIFEST = {"javascript", "kotlin", "java", "cpp", "sql"}

# Directory NAMES the census never descends into: VCS, deps, build output, caches. Virtualenvs
# are recognised by their pyvenv.cfg, not by name.
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "target",
    "build",
    "dist",
    "vendor",
    ".next",
    ".nuxt",
    ".gradle",
    "coverage",
    "deps",
    "_build",
    "Pods",
    ".dart_tool",
    "cache",
    "tmp",
    "log",
    "logs",
}
# Repo-relative PATHS the template itself owns — skipped so the scaffold never reads as project
# code, while a project's own scripts/ or tools/ still count.
TEMPLATE_PATHS = {
    "docs",
    "workflow",
    "tools/gmd",
    "scripts/sdd",
    "scripts/lint-gmd.sh",
    "scripts/tune-project.py",
    "install.sh",
}
# Only names that are safe inside a sourced shell file and a Markdown code span reach hooks.env
# and the profile; anything else (spaces, $, quotes, backticks) is reported and left out.
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9._@+-][A-Za-z0-9._/@+-]*$")
MAX_DEPTH = 6
TEST_DIR_RE = re.compile(r"(^|[_.-])tests?($|[_.-])|^__tests?__$|^specs?$|^e2e$|^testing$", re.I)
# Whole-token match so `spectrum/`, `inspector/`, `latest/` still count as source.
NOT_SRC_RE = re.compile(
    r"(^|[_.-])(tests?|specs?|e2e|fixtures?|samples?|examples?|"
    r"bench(marks?)?|demos?|mocks?|old|legacy|deprecated|scratch|testdata)"
    r"($|[_.-])",
    re.I,
)
UI_DIRS = ["ui", "frontend", "web", "client", "webapp", "app/frontend"]
STATIC_UI_DIRS = ["public", "static", "assets"]  # plain browser JS, no build step
MIGRATION_DIRS = [
    "alembic",
    "migrations",
    "db/migrate",
    "db/migrations",
    "prisma",
    "src/main/resources/db/migration",
    "priv/repo/migrations",
]
WORKSPACE_DIRS = ["packages", "apps", "services", "libs", "crates", "modules"]
DOC_EXTS = [".md", ".sh", ".json", ".yaml", ".yml", ".toml", ".txt"]

FRAMEWORKS = {  # manifest keyword -> display name
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "celery": "Celery",
    "react": "React",
    "next": "Next.js",
    "vue": "Vue",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "express": "Express",
    "@nestjs/core": "NestJS",
    "fastify": "Fastify",
    "vite": "Vite",
    "prisma": "Prisma",
    "gin-gonic/gin": "Gin",
    "labstack/echo": "Echo",
    "gofiber/fiber": "Fiber",
    "actix-web": "Actix Web",
    "axum": "Axum",
    "rocket": "Rocket",
    "tokio": "Tokio",
    "spring-boot": "Spring Boot",
    "ktor": "Ktor",
    "rails": "Rails",
    "sinatra": "Sinatra",
    "laravel/framework": "Laravel",
    "symfony/": "Symfony",
    "phoenix": "Phoenix",
    "Microsoft.AspNetCore": "ASP.NET Core",
    "flutter": "Flutter",
    "vapor": "Vapor",
}
DATABASES = {  # keyword (compose/manifest) -> display name
    "postgres": "PostgreSQL",
    "psycopg": "PostgreSQL",
    "asyncpg": "PostgreSQL",
    '"pg"': "PostgreSQL",
    "mysql": "MySQL",
    "mariadb": "MariaDB",
    "sqlite": "SQLite",
    "mongo": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "opensearch": "OpenSearch",
    "cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "lancedb": "LanceDB",
    "duckdb": "DuckDB",
}
COMPOSE_FILES = ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
MAKE_TARGETS = {
    "test": ["test"],
    "lint": ["lint"],
    "type": ["typecheck", "type-check", "types"],
    "format": ["format-check", "fmt-check", "check-format"],
}


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


def skip_dir(parent: str, name: str, rel: str = "") -> bool:
    return (
        name in SKIP_DIRS
        or name.startswith(".")
        or name.endswith(".egg-info")
        or (rel in TEMPLATE_PATHS)
        or os.path.isfile(os.path.join(parent, name, "pyvenv.cfg"))
    )


def safe_paths(paths: list[str], dropped: list[str]) -> list[str]:
    ok = []
    for p in paths:
        if SAFE_PATH_RE.match(p) and ".." not in p.split("/"):
            ok.append(p)
        else:
            dropped.append(p)
    return ok


def find_manifests(root: Path, pattern: str) -> list[Path]:
    """Manifests at the root and up to two levels down (monorepo members)."""
    hits: list[Path] = []
    for depth_glob in (pattern, f"*/{pattern}", f"*/*/{pattern}"):
        for p in root.glob(depth_glob):
            parts = p.relative_to(root).parts
            if not any(
                skip_dir(str(root.joinpath(*parts[:i])), parts[i]) for i in range(len(parts) - 1)
            ):
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
        dirnames[:] = [
            d
            for d in dirnames
            if len(rel) < MAX_DEPTH and not skip_dir(dirpath, d, "/".join(rel + (d,)))
        ]
        for f in filenames:
            if "/".join(rel + (f,)) in TEMPLATE_PATHS:
                continue
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
def detect(root: Path, force_langs: list[str] | None = None, force_pkg: str = "") -> dict:
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
    if (
        "typescript" in langs
        and "javascript" in langs
        and counts["javascript"] < counts["typescript"]
    ):
        langs.remove("javascript")
    langs.sort(key=lambda k: -counts[k])
    greenfield = not langs  # judged on what exists, before any --lang override
    if force_langs:
        langs = force_langs

    info: dict = {
        "langs": langs,
        "counts": counts,
        "minor": minor,
        "manifests": manifests,
        "greenfield": greenfield,
    }

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
        if not isinstance(pkgjson, dict):
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
                if (
                    d.is_dir()
                    and (d / "__init__.py").is_file()
                    and not skip_dir(str(base), d.name)
                    and not NOT_SRC_RE.search(d.name)
                    and d.name != "scripts"
                ):
                    pkg = d.name
                    break
            if pkg:
                break
    info["package"] = force_pkg or pkg or (slug(name) if name else "")

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
    ui = next(
        (
            d
            for d in UI_DIRS
            if (root / d).is_dir()
            and (
                (root / d / "package.json").is_file()
                or has_src_files(root, d, [".tsx", ".jsx", ".vue", ".svelte"])
            )
        ),
        "",
    )
    if not ui:
        ui = next(
            (
                d
                for d in STATIC_UI_DIRS
                if sum(by_top.get(d, Counter())[e] for e in (".js", ".ts", ".jsx", ".tsx")) >= 3
            ),
            "",
        )
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
    extra = sorted(
        (
            (sum(c[e] for e in exts), d)
            for d, c in by_top.items()
            if d not in covered
            and d not in tests
            and d != ui
            and d not in migrations
            and not NOT_SRC_RE.search(d)
            and (root / d).is_dir()
        ),
        reverse=True,
    )
    src += [d for n, d in extra if n > 0]

    ws_markers = [
        f
        for f in (
            "pnpm-workspace.yaml",
            "lerna.json",
            "nx.json",
            "turbo.json",
            "go.work",
            "rush.json",
        )
        if (root / f).is_file()
    ]
    if pkgjson.get("workspaces"):
        ws_markers.append("package.json#workspaces")
    if "workspace" in toml_load(root / "Cargo.toml") or re.search(
        r"^\[workspace\]", read(root / "Cargo.toml"), re.M
    ):
        ws_markers.append("Cargo.toml#workspace")
    if py and "workspace" in py.get("tool", {}).get("uv", {}):
        ws_markers.append("pyproject.toml#tool.uv.workspace")
    info["monorepo"] = bool(ws_markers)
    info["workspace_markers"] = ws_markers
    if info["monorepo"]:
        src += [d for d in WORKSPACE_DIRS if (root / d).is_dir() and d not in src]
    dropped: list[str] = []
    info.update(
        src_roots=safe_paths(src, dropped),
        test_roots=safe_paths(tests, dropped),
        ui=(safe_paths([ui], dropped) or [""])[0] if ui else "",
        migrations=safe_paths(migrations, dropped),
        unsafe_paths=dropped,
    )
    info["root_sources"] = sum(at_root[e] for e in exts)
    info["compose"] = next((f for f in COMPOSE_FILES if (root / f).is_file()), "")
    compose_text = read(root / info["compose"]) if info["compose"] else ""
    info["compose_services"] = compose_services(compose_text)
    docker_text = compose_text + "".join(
        read(p) for p in list(root.glob("Dockerfile*")) + list(root.glob("docker/*")) if p.is_file()
    )
    info["dockerfile"] = (root / "Dockerfile").is_file() or any(root.glob("docker/Dockerfile*"))
    # Container conventions CLAUDE.md assumes — recorded only when the project shows them.
    info["docker_dev"] = "dev" in info["compose_services"]
    info["docker_test_output"] = "/test-output" in compose_text
    info["docker_venv"] = bool(re.search(r"/opt/[A-Za-z0-9_.-]+-venv", docker_text))

    # frameworks + databases from manifest/compose text
    blob = "\n".join(read(root / p) for ps in manifests.values() for p in ps).lower()
    info["manifest_blob"] = blob
    info["frameworks"] = sorted(
        {
            v
            for k, v in FRAMEWORKS.items()
            if re.search(rf"[\"'/\s=@]{re.escape(k.lower())}(?![a-z0-9_-])", blob)
        }
    )
    db_blob = blob + "\n" + (read(root / info["compose"]).lower() if info["compose"] else "")
    info["databases"] = sorted({v for k, v in DATABASES.items() if k in db_blob})

    scripts = pkgjson.get("scripts")
    if not isinstance(scripts, dict):
        scripts = {}
    info["npm_scripts"] = {"test": "npm test"} if "test" in scripts else {}
    for want, names in (
        ("lint", ["lint"]),
        ("type", ["typecheck", "type-check", "tsc"]),
        ("format", ["format:check", "prettier:check", "fmt:check"]),
    ):
        hit = next((n for n in names if n in scripts), None)
        if hit:
            info["npm_scripts"][want] = f"npm run {hit}"
    targets = make_targets(root)
    info["make"] = {
        k: f"make {next(t for t in v if t in targets)}"
        for k, v in MAKE_TARGETS.items()
        if any(t in targets for t in v)
    }
    info["build_tool"] = (
        "./gradlew"
        if (root / "gradlew").is_file()
        else (
            "gradle"
            if any(root.glob("build.gradle*"))
            else ("mvn" if (root / "pom.xml").is_file() else "")
        )
    )
    return info


def compose_services(text: str) -> list[str]:
    """Top-level service names from a compose file (indentation-based; no YAML dependency)."""
    m = re.search(r"^services:[ \t]*\n((?:[ \t]+.*\n|[ \t]*\n)*)", text + "\n", re.M)
    if not m:
        return []
    body = m.group(1)
    indents = [len(x) for x in re.findall(r"^([ \t]+)\S", body, re.M)]
    if not indents:
        return []
    ind = min(indents)
    return re.findall(rf"^[ \t]{{{ind}}}([A-Za-z0-9_.-]+):", body, re.M)


def norm_db(raw: str) -> str:
    key = raw.strip().lower()
    aliases = {
        "postgresql": "postgres",
        "pg": "postgres",
        "mongodb": "mongo",
        "mongo": "mongo",
        "mariadb": "mariadb",
        "mysql": "mysql",
        "sqlite3": "sqlite",
    }
    return DATABASES.get(aliases.get(key, key), raw.strip())


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
    sys.stderr.write(
        "\n  No code or language manifests found — this looks like a from-scratch "
        "project.\n  Answer a few questions so the scaffold is tuned to it "
        "(Enter accepts the default).\n\n"
    )
    info["name"] = args.name or pr.ask("Project name", info.get("name") or root.name)
    info["description"] = args.description or pr.ask(
        "One-line description", info.get("description", "")
    )
    langs = norm_langs(args.lang) if args.lang else []
    while not langs:
        langs = norm_langs(pr.ask(f"Language(s), primary first ({' '.join(LANGS)})", "python"))
    info["langs"] = langs
    info["package"] = args.package or pr.ask("Package / module name", slug(info["name"]))
    hint = {
        "python": "e.g. FastAPI",
        "typescript": "e.g. React, Express",
        "go": "e.g. Gin",
        "rust": "e.g. Axum",
        "java": "e.g. Spring Boot",
        "ruby": "e.g. Rails",
        "sql": "e.g. pgTAP, sqitch",
    }
    fw = pr.ask(f"Frameworks ({hint.get(langs[0], 'comma-separated')}; blank for none)", "")
    info["frameworks"] = [f.strip() for f in fw.split(",") if f.strip()]
    db = args.db or pr.ask("Database (postgres, mysql, sqlite, mongodb, none)", "none")
    info["databases"] = [] if db.lower() in ("", "none", "-") else [norm_db(db)]
    ui = args.ui if args.ui is not None else pr.ask("Frontend/UI directory (blank for none)", "")
    dropped: list[str] = []
    info["ui"] = (safe_paths([ui.strip().strip("/")], dropped) or [""])[0] if ui.strip() else ""
    info["unsafe_paths"] = dropped
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
    info["src_roots"] = safe_paths(src, info["unsafe_paths"])
    info["test_roots"] = safe_paths(tests, info["unsafe_paths"])
    info["migrations"] = (
        ["alembic"]
        if info["databases"] and langs[0] == "python"
        else (["migrations"] if info["databases"] else [])
    )
    # Never create directories unasked: without a terminal only an explicit --skeleton does.
    if args.skeleton is None:
        dirs = src + tests + ([info["ui"]] if info["ui"] else []) + info["migrations"]
        args.skeleton = pr.interactive and pr.ask(
            f"Create the directory skeleton ({', '.join(dirs)})? [Y/n]", "y"
        ).lower().startswith("y")


# --------------------------------------------------------------------------------------------
# derivation: commands, corpus, hooks.env
# --------------------------------------------------------------------------------------------
def commands(info: dict, root: Path) -> dict[str, str]:
    """Commands the project has evidence for. Greenfield: the idiomatic set, all *proposed*."""
    if not info["langs"]:
        return {}
    primary = info["langs"][0]
    # The /opt/<pkg>-venv container convention is used only when proposed (greenfield) or when
    # the project's Docker files show it; otherwise the host interpreter.
    venv_py = (
        f"/opt/{info['package'] or '{project_package}'}-venv/bin/python"
        if info["greenfield"] or info.get("docker_venv")
        else "python3"
    )
    build = info.get("build_tool") or ("./gradlew" if info["greenfield"] else "")
    if primary in ("java", "kotlin") and not build:
        return {}  # no build tool, no evidence of how the JVM code is built
    fmt = {"py": venv_py, "src": info["src_roots"][0] if info["src_roots"] else ".", "build": build}
    blob = info.get("manifest_blob", "")
    out: dict[str, str] = {}
    for kind, (cmd, markers) in LANGS[primary]["cmds"].items():
        if cmd == "—":
            continue
        if info["greenfield"] or has_evidence(root, blob, markers):
            out[kind] = cmd.format(**fmt)
    if build == "mvn":  # Maven phases/plugin goals differ from Gradle task names
        mvn = {
            "test": "mvn test",
            "lint": "mvn checkstyle:check",
            "type": "mvn compile",
            "format": "mvn spotless:check",
        }
        out = {k: mvn[k] for k in out}
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
    # Wrap in the container only as far as the compose file proves: a `dev` service, and the
    # /test-output mount for the tee.
    if info.get("docker_dev"):
        tee = f" 2>&1 | tee /test-output/{log}.log" if info.get("docker_test_output") else ""
        return f'`docker compose exec dev bash -c "{cmd}{tee}"`'
    return f"`{cmd}`"


def corpus(info: dict) -> tuple[list[str], list[str]]:
    roots: list[str] = []
    for d in (
        info["src_roots"]
        + info["test_roots"]
        + ([info["ui"]] if info["ui"] else [])
        + info["migrations"]
        + ["docs", "workflow"]
    ):
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


ENV_MARKER = "# tune-project:generated"
ENV_KEY_RE = re.compile(r"^[A-Z_]+=.*$", re.M)


def env_keys(text: str) -> str:
    """The assignment lines only — comments and blank lines do not affect ownership."""
    return "\n".join(ENV_KEY_RE.findall(text))


def env_digest(text: str) -> str:
    return hashlib.sha256(env_keys(text).encode()).hexdigest()[:16]


def env_regenerable(current: str, example: str) -> bool:
    """hooks.env belongs to the generator while it is still the example (any version of its
    comments) or still exactly what a previous run generated (recorded digest matches)."""
    if example and env_keys(current) == env_keys(example):
        return True
    m = re.search(rf"^{re.escape(ENV_MARKER)} sha256=([0-9a-f]+)", current, re.M)
    return bool(m) and m.group(1) == env_digest(current)


def hooks_env(info: dict) -> str:
    roots, exts = corpus(info)
    class_exts: list[str] = []
    for key in info["langs"]:
        class_exts += [e for e in LANGS[key]["class_exts"] if e not in class_exts]
    # No class-bearing language (Go, Rust, Elixir, SQL) -> a never-matching regex keeps the
    # gate inert.
    gate_re = f"\\.({'|'.join(class_exts)})$" if class_exts else "^$"
    langs = ", ".join(LANGS[k]["label"] for k in info["langs"]) or "no language detected"
    # Single-quoted: this file is sourced by every hook. Paths were already filtered through
    # SAFE_PATH_RE, so no value can contain a quote.
    body = f"""
# Source root(s) the adr-gate scans for new class definitions (space-separated, repo-relative).
SRC_DIR='{" ".join(info["src_roots"]) or "src"}'

# Where ADRs live (adr-gate greps these for class-name matches).
ADR_DIR='docs/architecture/adr'

# Space-separated corpus roots. Bare grep into these is redirected to rmx by enforce-rmx-grep.
CORPUS_PATHS='{" ".join(roots)}'

# Source-file extensions considered "corpus" content.
CORPUS_EXTS='{" ".join(exts)}'

# File-glob (extended regex) adr-gate inspects for new class defs. adr-gate matches `class X`
# declarations only, so languages without classes (Go, Rust, Elixir, SQL) get the never-matching
# '^$' and the gate is inert for them.
ADR_GATE_FILE_RE='{gate_re}'
"""
    return (
        f"""{ENV_MARKER} sha256={env_digest(body)}
# Hook configuration — generated by scripts/tune-project.py from the detected layout
# ({langs}). Re-running the tuner regenerates it while the values above are unchanged; edit any
# value and the file becomes project-owned (never overwritten again).
# Values mirror .claude/PROJECT_PROFILE.md (Directory layout + Discovery corpus).
"""
        + body
    )


# --------------------------------------------------------------------------------------------
# PROJECT_PROFILE.md
# --------------------------------------------------------------------------------------------
# Template-shipped values that are defaults rather than project facts — replaceable like `{…}`.
PRISTINE = {
    "UI (if any)": "`ui/`",
    "Source extensions": "`.py .ts .tsx .js .md .sh .json .yaml .toml`",
}
FIELD_RE = re.compile(r"^- \*\*([^*]+):\*\* (.*)$", re.M)
EXIT_NOT_TUNED = 3  # install.sh records this as "skipped", not "tuned"
DETECT_BEGIN = "<!-- tune-project:begin (generated — re-run scripts/tune-project.py) -->"
DETECT_END = "<!-- tune-project:end -->"


TEMPLATE_TOKENS = ("{PROJECT_NAME}", "{project_package}", "{project_db}")


def untouched(key: str, value: str) -> bool:
    """A value is still the template's when it IS a `{…}` placeholder, carries a template
    token, is an elided `… cmd` example, or equals a shipped default — never merely because a
    project value happens to contain braces (e.g. `ruff check {src,tests}`)."""
    v = value.strip()
    return (
        (v.startswith("{") and v.endswith("}"))
        or any(t in v for t in TEMPLATE_TOKENS)
        or v.startswith("`…")
        or v.startswith("…")
        or PRISTINE.get(key) == v
    )


def profile_is_tuned(text: str) -> bool:
    """A profile whose identity + stack were filled (by a person or a previous run) is
    project-owned. Hand-tuned profiles may rename fields (e.g. `Language:`), so a missing
    field counts as filled; only a surviving placeholder counts as untuned."""
    fields = dict(FIELD_RE.findall(text))
    if "Name" not in fields or untouched("Name", fields["Name"]):
        return False
    return not any(untouched(k, fields[k]) for k in ("Language(s)", "Language") if k in fields)


def drift(text: str, info: dict, say) -> None:
    """Tuned profiles are project-owned; surface where detection now disagrees."""
    fields = dict(FIELD_RE.findall(text))
    recorded = fields.get("Language(s)", fields.get("Language", ""))
    missing = [LANGS[k]["label"] for k in info["langs"] if LANGS[k]["label"] not in recorded]
    if missing:
        say(f"drift: detected {', '.join(missing)} not recorded in the profile's languages")
    src = fields.get("Source root", "")
    new_roots = [d for d in info["src_roots"] if f"`{d}/`" not in src and d not in src]
    if src and new_roots:
        say(f"drift: source roots not in the profile: {', '.join(new_roots)}")


def fill_profile(
    text: str, info: dict, cmds: dict[str, str], with_block: bool = True
) -> tuple[str, list[str]]:
    roots, exts = corpus(info)
    pkg = info["package"]
    python_first = info["langs"][:1] == ["python"]
    logs = (
        ("pytest", "ruff", "mypy", "black")
        if python_first
        else ("test", "lint", "typecheck", "format")
    )
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
    prose_re = r"^All commands run in Docker \(see CLAUDE\.md\)\. The venv is at .*$"
    venv_proven = info["greenfield"] or info.get("docker_venv")
    if python_first and pkg and venv_proven and (info["greenfield"] or info.get("docker_dev")):
        text = text.replace("/opt/{project_package}-venv", f"/opt/{pkg}-venv")
    elif info["greenfield"] or info.get("docker_dev"):
        text = re.sub(
            prose_re,
            "All commands run in Docker (see CLAUDE.md) via `docker compose exec dev`.",
            text,
            flags=re.M,
        )
    else:
        svcs = ", ".join(info.get("compose_services", []))
        why = (
            f"`{info['compose']}` has no `dev` service ({svcs or 'no services'})"
            if info.get("compose")
            else "no docker compose file was found"
        )
        text = re.sub(
            prose_re,
            f"These run on the host as detected — {why}. Either set up the "
            "`dev` container (SETUP.md) or adapt CLAUDE.md's Docker-only rule.",
            text,
            flags=re.M,
        )

    # Evidence section — replaced wholesale on every run.
    ev = [DETECT_BEGIN, "", "## Install detection {#install-detection}", ""]
    counts = info["counts"]
    if info["greenfield"]:
        ev.append(
            "- **Mode:** from scratch — values above came from install-time answers; "
            "commands are proposals until the toolchain exists"
        )
    else:
        ev.append(
            "- **Mode:** existing codebase — values above were detected; a command shown as "
            "none has no config/dependency/script evidence"
        )
        ev.append(
            "- **Source files:** "
            + ", ".join(f"{LANGS[k]['label']} {counts[k]}" for k in info["langs"])
        )
        if info["minor"]:
            ev.append(
                "- **Also present (minor, not tuned for):** "
                + ", ".join(f"{LANGS[k]['label']} {counts[k]}" for k in info["minor"])
            )
        ev.append(
            "- **Manifests:** "
            + (", ".join(f"`{p}`" for ps in info["manifests"].values() for p in ps[:4]) or "—")
        )
        if info["root_sources"]:
            ev.append(
                f"- **Repo-root sources:** {info['root_sources']} file(s) at the top level "
                "(not expressible as a SRC_DIR root)"
            )
    if info.get("monorepo"):
        ev.append("- **Monorepo:** " + ", ".join(f"`{m}`" for m in info["workspace_markers"]))
    if info.get("unsafe_paths"):
        ev.append(
            "- **Skipped paths (unsafe characters):** "
            + ", ".join(repr(p) for p in info["unsafe_paths"])
        )
    if not any(LANGS[k]["class_exts"] for k in info["langs"]) and info["langs"]:
        ev.append(
            "- **ADR gate:** inert — it matches `class X` declarations and none of the "
            "detected languages declare classes"
        )
    docker = (
        [f"`{info['compose']}` (services: {', '.join(info.get('compose_services', [])) or '—'})"]
        if info.get("compose")
        else []
    )
    docker += ["Dockerfile"] if info.get("dockerfile") else []
    ev.append(
        "- **Docker:** "
        + (
            ", ".join(docker)
            or "none — CLAUDE.md assumes Docker; adapt it or set Docker up (SETUP.md)"
        )
    )
    ev += [
        "",
        "Detection is a starting point: confirm every value, then finish the tuning steps in",
        "`docs/ONBOARDING.md` (placeholders in CLAUDE.md, stack-specific Development Commands,",
        "Docker setup, agent overlays, constitution).",
        "",
        DETECT_END,
    ]
    block = "\n".join(ev)
    if not with_block:
        return text, filled
    if DETECT_BEGIN in text:
        text = re.sub(
            re.escape(DETECT_BEGIN) + r".*?" + re.escape(DETECT_END),
            lambda _: block,
            text,
            flags=re.S,
        )
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
    ap.add_argument(
        "--dry-run", action="store_true", help="report + print hooks.env; write nothing"
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    say = lambda s: sys.stderr.write(f"  {s}\n")  # noqa: E731
    prof_p = root / ".claude/PROJECT_PROFILE.md"
    prof_text = read(prof_p) if prof_p.is_file() else ""
    tuned = bool(prof_text) and profile_is_tuned(prof_text)
    forced = norm_langs(args.lang) if args.lang else []
    if args.lang and not forced:
        say(f"!! --lang={args.lang}: no known language — known: {', '.join(LANGS)}")
        return 2
    # Overrides go through detection so the layout is recomputed for them.
    info = detect(root, forced or None, args.package or "")
    pr = Prompter(enabled=not (args.no_prompt or args.dry_run or tuned))

    if tuned:
        say(
            "PROJECT_PROFILE.md is already tuned (project-owned): only placeholder fields and the "
            "generated detection block are refreshed"
        )
    if info["greenfield"] and not tuned:
        if not pr.interactive and not args.lang:
            say(
                "!! from-scratch project and no terminal to prompt on. Re-run interactively "
                "(python3 scripts/tune-project.py) or pass --lang=… "
                "[--name= --package= --db= --ui=]. Nothing tuned."
            )
            return EXIT_NOT_TUNED
        greenfield_questions(info, args, pr, root)
    elif not info["greenfield"]:
        # Flags override detection; prompts only fill identity gaps detection could not.
        info["name"] = args.name or info["name"] or pr.ask("Project name", root.name)
        info["description"] = (
            args.description
            or info["description"]
            or pr.ask("One-line description (blank to fill later)", "")
        )
        info["package"] = info["package"] or slug(info["name"])
        if args.db:
            info["databases"] = [norm_db(args.db)]
        if args.ui is not None:
            dropped: list[str] = info.setdefault("unsafe_paths", [])
            info["ui"] = (
                (safe_paths([args.ui.strip("/")], dropped) or [""])[0] if args.ui.strip("/") else ""
            )
        info["os"] = args.os or ""

    cmds = commands(info, root)
    say(
        f"languages: {', '.join(LANGS[k]['label'] for k in info['langs']) or '—'}"
        + (" (monorepo)" if info.get("monorepo") else "")
        + (
            f"   minor: {', '.join(LANGS[k]['label'] for k in info['minor'])}"
            if info.get("minor")
            else ""
        )
    )
    say(f"source:    {' '.join(info['src_roots']) or '—'}")
    say(
        f"tests:     {' '.join(info['test_roots']) or '—'}   ui: {info['ui'] or '—'}"
        f"   migrations: {' '.join(info['migrations']) or '—'}"
        f"   docker: {info.get('compose') or ('Dockerfile' if info.get('dockerfile') else '—')}"
    )
    if info.get("frameworks"):
        say(f"frameworks: {', '.join(info['frameworks'])}")
    if info.get("databases"):
        say(f"storage:   {', '.join(info['databases'])}")
    for k in ("test", "lint", "type", "format"):
        say(
            f"{k + ':':<10} {cmds.get(k, '— (no evidence)')}"
            + (" (proposed)" if info["greenfield"] and cmds.get(k) else "")
        )

    for p in info.get("unsafe_paths", []):
        say(f"!! skipped path with unsafe characters: {p!r}")
    if tuned:
        drift(prof_text, info, say)
    if info["greenfield"] and tuned:
        return 0  # a hand-tuned from-scratch profile (e.g. design-only): nothing to detect
    if args.dry_run:
        sys.stdout.write(hooks_env(info))
        return 0

    # hooks.env — (re)generate while the generator still owns it.
    env_p, ex_p = root / ".claude/hooks/hooks.env", root / ".claude/hooks/hooks.env.example"
    if not env_p.exists() or env_regenerable(read(env_p), read(ex_p)):
        env_p.parent.mkdir(parents=True, exist_ok=True)
        env_p.write_text(hooks_env(info), encoding="utf-8")
        say("wrote .claude/hooks/hooks.env (tuned to detected layout)")
    else:
        say(
            ".claude/hooks/hooks.env preserved (project-edited) — detected: "
            f"SRC_DIR='{' '.join(info['src_roots'])}' CORPUS_PATHS='{' '.join(corpus(info)[0])}'"
        )

    if prof_text:
        # A hand-tuned profile that never had a detection block does not get one appended.
        with_block = not tuned or DETECT_BEGIN in prof_text
        text, filled = fill_profile(prof_text, info, cmds, with_block)
        if text != prof_text:
            prof_p.write_text(text, encoding="utf-8")
        say(f"filled PROJECT_PROFILE.md: {', '.join(filled) or 'nothing left to fill'}")
        left = [k for k, v in FIELD_RE.findall(text) if untouched(k, v)]
        if left:
            say(f"still to fill by hand: {', '.join(left)}")

    if info["greenfield"] and args.skeleton:
        for d in (
            info["src_roots"]
            + info["test_roots"]
            + ([info["ui"]] if info["ui"] else [])
            + info["migrations"]
        ):
            p = root / d
            if root not in p.resolve().parents:
                say(f"!! not creating {d!r}: outside the project root")
                continue
            if not p.exists():
                p.mkdir(parents=True)
                (p / ".gitkeep").touch()
                say(f"created {d}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
