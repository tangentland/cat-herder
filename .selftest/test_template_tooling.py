"""Self-tests for the cat-herder template's own tooling.

Covers scripts/tune-project.py, install.sh scaffolding, .claude/hooks/adr-gate.sh and
.claude/statusline.sh. Stdlib unittest only; every fixture is built in a temp dir from a
{path: body} dict, and every tool runs as a real subprocess — no mocks.

Run:  python3 -m unittest discover -s .selftest -v     (or .selftest/run.sh)
This directory is template-only: .scaffoldignore keeps it out of scaffolded projects.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TUNE = REPO / "scripts/tune-project.py"
PROFILE = REPO / ".claude/PROJECT_PROFILE.md"
ENV_EX = REPO / ".claude/hooks/hooks.env.example"
HAS_JQ = shutil.which("jq") is not None


def mk(root: Path, files: dict) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)


def scaffold(root: Path) -> None:
    """What install.sh leaves behind before tuning: the profile, the hooks.env example seeded
    as hooks.env (wire_sdd), and the template-owned scripts/sdd dir."""
    (root / ".claude/hooks").mkdir(parents=True, exist_ok=True)
    shutil.copy(PROFILE, root / ".claude/PROJECT_PROFILE.md")
    shutil.copy(ENV_EX, root / ".claude/hooks/hooks.env.example")
    shutil.copy(ENV_EX, root / ".claude/hooks/hooks.env")
    (root / "scripts/sdd").mkdir(parents=True, exist_ok=True)
    (root / "scripts/sdd/common.sh").write_text("#!/bin/sh\n")


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TUNE), "--root", str(root), *args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def envvars(root: Path) -> dict:
    out = {}
    for line in (root / ".claude/hooks/hooks.env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k] = v.strip("\"'")
    return out


def profile(root: Path) -> str:
    return (root / ".claude/PROJECT_PROFILE.md").read_text()


def field(root: Path, key: str):
    for line in profile(root).splitlines():
        if line.startswith(f"- **{key}:** "):
            return line.split(":** ", 1)[1]
    return None


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)


# ------------------------------------------------------------------------------ tune-project
class PythonSrcLayout(Base):
    def setUp(self) -> None:
        super().setUp()
        scaffold(self.root)
        mk(
            self.root,
            {
                "pyproject.toml": '[project]\nname="acme-svc"\ndescription="Acme svc"\n'
                'dependencies=["fastapi","psycopg"]\n[tool.ruff]\nline-length=100\n',
                "src/acme_svc/__init__.py": "",
                "src/acme_svc/a.py": "x=1\n",
                "src/acme_svc/b.py": "",
                "tests/test_a.py": "def test(): pass\n",
                "docker-compose.yml": "services:\n  db:\n    image: postgres:16\n",
            },
        )

    def test_detect_and_fill(self):
        r = run(self.root, "--no-prompt")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(field(self.root, "Name"), "acme-svc")
        self.assertEqual(field(self.root, "Package / module"), "acme_svc")
        self.assertEqual(field(self.root, "Language(s)"), "Python")
        self.assertIn("FastAPI", field(self.root, "Frameworks"))
        self.assertIn("PostgreSQL", field(self.root, "Storage"))
        self.assertEqual(field(self.root, "Source root"), "`src/acme_svc/`")
        # evidence-gated: pytest (tests/test_*.py) + ruff ([tool.ruff]) yes; mypy/black no
        self.assertIn("pytest", field(self.root, "Test"))
        self.assertIn("ruff", field(self.root, "Lint"))
        self.assertIn("none detected", field(self.root, "Type check"))
        self.assertIn("none detected", field(self.root, "Format check"))
        self.assertEqual(envvars(self.root)["SRC_DIR"], "src/acme_svc")
        self.assertEqual(envvars(self.root)["ADR_GATE_FILE_RE"], r"\.(py)$")
        for bad in ("docs", "workflow", "tools", ".claude", "scripts"):
            self.assertNotIn(bad, envvars(self.root)["SRC_DIR"].split())

    def test_compose_without_dev_service_is_not_wrapped(self):
        run(self.root, "--no-prompt")
        test = field(self.root, "Test")
        self.assertNotIn("docker compose", test)
        self.assertNotIn("/opt/", test)
        self.assertIn("no `dev` service", profile(self.root))

    def test_idempotent(self):
        run(self.root, "--no-prompt")
        p1, e1 = profile(self.root), (self.root / ".claude/hooks/hooks.env").read_text()
        r = run(self.root, "--no-prompt")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(p1, profile(self.root))
        self.assertEqual(e1, (self.root / ".claude/hooks/hooks.env").read_text())
        self.assertEqual(p1.count("tune-project:begin"), 1)

    def test_placeholder_only_fill(self):
        p = self.root / ".claude/PROJECT_PROFILE.md"
        p.write_text(
            p.read_text()
            .replace("- **Frameworks:** {e.g. FastAPI, React}", "- **Frameworks:** Mine")
            .replace("- **Lint:** `… ruff check .", "- **Lint:** `ruff check {src,tests}` #")
        )
        run(self.root, "--no-prompt")
        self.assertEqual(field(self.root, "Frameworks"), "Mine")
        self.assertTrue(field(self.root, "Lint").startswith("`ruff check {src,tests}`"))
        self.assertEqual(field(self.root, "Name"), "acme-svc")

    def test_hooks_env_preserved_when_edited(self):
        run(self.root, "--no-prompt")
        env = self.root / ".claude/hooks/hooks.env"
        env.write_text(env.read_text().replace("ADR_DIR='docs/architecture/adr'", "ADR_DIR='adr'"))
        edited = env.read_text()
        mk(self.root, {"lib2/x.py": "", "lib2/y.py": "", "lib2/z.py": ""})
        r = run(self.root, "--no-prompt")
        self.assertIn("preserved", r.stderr)
        self.assertEqual(edited, env.read_text())

    def test_hooks_env_regenerated_while_generator_owned(self):
        run(self.root, "--no-prompt")
        mk(self.root, {"lib2/x.py": "", "lib2/y.py": "", "lib2/z.py": ""})
        r = run(self.root, "--no-prompt")
        self.assertIn("lib2", envvars(self.root)["SRC_DIR"].split())
        self.assertIn("drift: source roots not in the profile: lib2", r.stderr)

    def test_hooks_env_regenerated_when_absent(self):
        (self.root / ".claude/hooks/hooks.env").unlink()
        run(self.root, "--no-prompt")
        self.assertEqual(envvars(self.root)["SRC_DIR"], "src/acme_svc")

    def test_dry_run_writes_nothing(self):
        before = profile(self.root)
        r = run(self.root, "--dry-run")
        self.assertIn("SRC_DIR='src/acme_svc'", r.stdout)
        self.assertEqual(before, profile(self.root))


class DockerDevEvidence(Base):
    def test_dev_service_mount_and_venv_wrap(self):
        scaffold(self.root)
        mk(
            self.root,
            {
                "pyproject.toml": '[project]\nname="svc"\ndependencies=["pytest"]\n',
                "svc/__init__.py": "",
                "svc/a.py": "",
                "svc/b.py": "",
                "compose.yaml": "services:\n  dev:\n    build: .\n    volumes:\n"
                "      - ./out:/test-output\n  db:\n    image: postgres\n",
                "Dockerfile": "RUN python3 -m venv /opt/svc-venv\n",
            },
        )
        run(self.root, "--no-prompt")
        self.assertEqual(
            field(self.root, "Test"),
            '`docker compose exec dev bash -c "/opt/svc-venv/bin/python -m pytest -v'
            ' 2>&1 | tee /test-output/pytest.log"`',
        )


class Safety(Base):
    def test_shell_unsafe_dir_names_never_reach_hooks_env(self):
        scaffold(self.root)
        evil = "x$(touch PWNED)"
        mk(
            self.root,
            {
                "requirements.txt": "",
                f"{evil}/a.py": "",
                f"{evil}/b.py": "",
                f"{evil}/c.py": "",
                "app/m.py": "",
                "app/n.py": "",
                "app/o.py": "",
            },
        )
        r = run(self.root, "--no-prompt")
        self.assertIn("unsafe characters", r.stderr)
        self.assertNotIn("PWNED", (self.root / ".claude/hooks/hooks.env").read_text())
        subprocess.run(
            ["bash", "-c", f". '{self.root}/.claude/hooks/hooks.env'"], cwd=self.root, check=True
        )
        self.assertFalse((self.root / "PWNED").exists())

    def test_skeleton_confined_to_root(self):
        scaffold(self.root)
        r = run(self.root, "--no-prompt", "--lang=py", "--name=x", "--ui=../escape", "--skeleton")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.root.parent / "escape").exists())

    def test_unknown_lang_is_an_error(self):
        scaffold(self.root)
        self.assertEqual(run(self.root, "--no-prompt", "--lang=bogus").returncode, 2)


class Layout(Base):
    def test_token_match_keeps_spectrum_and_project_scripts(self):
        scaffold(self.root)
        mk(
            self.root,
            {
                "requirements.txt": "requests\n",
                "spectrum/a.py": "",
                "spectrum/b.py": "",
                "spectrum/c.py": "",
                "scripts/etl1.py": "",
                "scripts/etl2.py": "",
                "samples/s.py": "",
                "old_tests/t.py": "",
            },
        )
        run(self.root, "--no-prompt")
        roots = envvars(self.root)["SRC_DIR"].split()
        self.assertIn("spectrum", roots)
        self.assertIn("scripts", roots)  # project-owned scripts count; scripts/sdd does not
        self.assertNotIn("samples", roots)
        self.assertNotIn("old_tests", roots)

    def test_virtualenv_by_pyvenv_cfg(self):
        scaffold(self.root)
        mk(
            self.root,
            {
                "requirements.txt": "",
                "app/a.py": "",
                "app/b.py": "",
                "app/c.py": "",
                "venv3.12/pyvenv.cfg": "",
                "venv3.12/lib/x.c": "",
                "venv3.12/lib/y.c": "",
                "venv3.12/lib/z.c": "",
                "venv3.12/lib/w.c": "",
            },
        )
        r = run(self.root, "--no-prompt")
        self.assertNotIn("C/C++", r.stderr)

    def test_sql_first_repo(self):
        scaffold(self.root)
        mk(
            self.root,
            {f"schema/t{i}.sql": "" for i in range(4)}
            | {f"queries/q{i}.sql": "" for i in range(3)}
            | {"tools2/qc.py": ""},
        )
        run(self.root, "--no-prompt")
        self.assertEqual(field(self.root, "Language(s)"), "SQL")
        self.assertEqual(envvars(self.root)["ADR_GATE_FILE_RE"], "^$")
        self.assertIn("none detected", field(self.root, "Test"))
        self.assertIn("ADR gate:** inert", profile(self.root))

    def test_maven_commands(self):
        scaffold(self.root)
        mk(
            self.root,
            {
                "pom.xml": "<project/>",
                **{f"src/main/java/A{i}.java": "class A {}" for i in range(3)},
            },
        )
        run(self.root, "--no-prompt")
        self.assertIn("mvn test", field(self.root, "Test"))
        self.assertIn("mvn compile", field(self.root, "Type check"))

    def test_java_without_build_tool_invents_nothing(self):
        scaffold(self.root)
        mk(self.root, {f"src/main/java/A{i}.java": "class A {}" for i in range(3)})
        run(self.root, "--no-prompt")
        self.assertIn("none detected", field(self.root, "Test"))


class TSMonorepo(Base):
    def test_monorepo(self):
        scaffold(self.root)
        mk(
            self.root,
            {
                "package.json": json.dumps(
                    {
                        "name": "@acme/mono",
                        "workspaces": ["packages/*"],
                        "scripts": {"test": "turbo test", "lint": "eslint ."},
                        "devDependencies": {"typescript": "5", "vitest": "1"},
                    }
                ),
                "tsconfig.json": "{}",
                "packages/a/src/index.ts": "",
                "packages/a/src/b.ts": "",
                "packages/b/src/c.tsx": "",
                "packages/b/package.json": "{}",
            },
        )
        r = run(self.root, "--no-prompt")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(field(self.root, "Language(s)"), "TypeScript")
        self.assertIn("packages", envvars(self.root)["SRC_DIR"].split())
        self.assertIn("npm test", field(self.root, "Test"))
        self.assertIn("npm run lint", field(self.root, "Lint"))
        self.assertIn("tsc --noEmit", field(self.root, "Type check"))
        self.assertIn("none detected", field(self.root, "Format check"))
        self.assertIn("Monorepo", profile(self.root))

    def test_non_object_package_json(self):
        scaffold(self.root)
        mk(self.root, {"package.json": "[1]", "src/a.js": "", "src/b.js": "", "src/c.js": ""})
        self.assertEqual(run(self.root, "--no-prompt").returncode, 0)


class AlreadyTuned(Base):
    def test_hand_tuned_profile_byte_identical(self):
        scaffold(self.root)
        mk(self.root, {"go.mod": "module example.com/x\n", "cmd/x/main.go": "package main\n"})
        p = self.root / ".claude/PROJECT_PROFILE.md"
        p.write_text("# Profile {#root}\n\n- **Name:** Mine\n- **Language:** Go\n")
        before = p.read_text()
        r = run(self.root, "--no-prompt")
        self.assertEqual(r.returncode, 0)
        self.assertIn("already tuned", r.stderr)
        self.assertEqual(before, p.read_text())

    def test_tuned_fields_kept_placeholders_filled_no_block_appended(self):
        scaffold(self.root)
        mk(self.root, {"go.mod": "module example.com/x\n", "cmd/x/main.go": "package main\n"})
        p = self.root / ".claude/PROJECT_PROFILE.md"
        p.write_text(
            p.read_text()
            .replace("- **Name:** {PROJECT_NAME}", "- **Name:** Mine")
            .replace(
                "- **Language(s):** {e.g. Python 3.14, TypeScript}", "- **Language(s):** Go (hand)"
            )
        )
        run(self.root, "--no-prompt")
        self.assertEqual(field(self.root, "Name"), "Mine")
        self.assertEqual(field(self.root, "Language(s)"), "Go (hand)")
        self.assertEqual(field(self.root, "Source root"), "`cmd/`")
        self.assertNotIn("tune-project:begin", profile(self.root))


class Greenfield(Base):
    def test_no_tty_no_lang_does_nothing(self):
        scaffold(self.root)
        before = profile(self.root)
        env_before = (self.root / ".claude/hooks/hooks.env").read_text()
        r = run(self.root, "--no-prompt")
        self.assertEqual(r.returncode, 3)
        self.assertIn("Nothing tuned", r.stderr)
        self.assertEqual(before, profile(self.root))
        self.assertEqual(env_before, (self.root / ".claude/hooks/hooks.env").read_text())

    def test_flags_only(self):
        scaffold(self.root)
        r = run(self.root, "--no-prompt", "--lang=py", "--name=New App", "--db=postgresql")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(field(self.root, "Package / module"), "new_app")
        self.assertIn("proposed", field(self.root, "Test"))
        self.assertEqual(field(self.root, "Storage"), "PostgreSQL")
        self.assertNotIn("{project_package}", profile(self.root).split("## Commands")[1][:300])

    def test_no_prompt_never_creates_skeleton(self):
        scaffold(self.root)
        run(self.root, "--no-prompt", "--lang=go", "--name=g")
        self.assertFalse((self.root / "cmd").exists())

    def test_explicit_skeleton(self):
        scaffold(self.root)
        run(self.root, "--no-prompt", "--lang=go", "--name=g", "--skeleton")
        self.assertTrue((self.root / "cmd/.gitkeep").exists())


# ------------------------------------------------------------------------------ install.sh
class Install(Base):
    RUNTIME = [
        ".refmatrix",
        ".tldr",
        ".agents",
        ".augment",
        "skills-lock.json",
        ".claude/settings.local.json",
        ".claude/scheduled_tasks.lock",
        ".selftest",
        "workflow/review-output",
        ".memory.db",
    ]
    # (.claude/hooks/hooks.env is excluded from the copy too, but wire_sdd then seeds a fresh one
    # from the example — so its presence after install is expected.)

    def _install(self, dest: Path, env=None, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(REPO / "install.sh"), str(dest), "--minimal", *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

    def _files(self, root: Path) -> list:
        return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())

    def test_runtime_state_never_copied_and_copy_paths_agree(self):
        a, b, shim = self.root / "a", self.root / "b", self.root / "shim"
        r = self._install(a, None, "--no-tune")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        shim.mkdir()
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if not os.path.isdir(d):
                continue
            for n in os.listdir(d):
                if n != "rsync" and not os.path.lexists(shim / n):
                    (shim / n).symlink_to(Path(d) / n)
        r = self._install(b, dict(os.environ, PATH=str(shim)), "--no-tune")
        self.assertIn("python fallback", r.stdout)
        self.assertEqual(self._files(a), self._files(b))
        for x in self.RUNTIME:
            self.assertFalse((a / x).exists(), f"scaffold copied runtime state: {x}")

    def test_existing_files_preserved_and_tuned(self):
        mk(self.root, {"go.mod": "module x\n", "cmd/a/main.go": "", "CLAUDE.md": "mine\n"})
        r = self._install(self.root, None, "--no-prompt")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual((self.root / "CLAUDE.md").read_text(), "mine\n")
        self.assertIn("wired:   gmd sdd tune", r.stdout)

    def test_greenfield_without_tty_reports_skipped(self):
        r = self._install(self.root, None, "--no-prompt")
        self.assertIn("nothing tuned", r.stderr)
        self.assertNotIn("tune", r.stdout.split("wired:")[1].splitlines()[0])


# ------------------------------------------------------------------------------ adr-gate
class ADRGate(Base):
    def setUp(self) -> None:
        super().setUp()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def _run(self, src_dir: str, file_path: str) -> subprocess.CompletedProcess:
        root = self.root
        (root / ".claude/hooks").mkdir(parents=True, exist_ok=True)
        for f in ("adr-gate.sh", "_common.sh"):
            shutil.copy(REPO / ".claude/hooks" / f, root / ".claude/hooks" / f)
        (root / ".claude/hooks/hooks.env").write_text(
            f"SRC_DIR='{src_dir}'\nADR_DIR='docs/adr'\nADR_GATE_FILE_RE='\\.(py|ts)$'\n"
        )
        mk(root, {"docs/adr/0001-widget.md": "# Widget\nWidgetStore decision\n"})
        payload = json.dumps(
            {"tool_input": {"file_path": file_path, "content": "class WidgetStore:\n  pass\n"}}
        )
        return subprocess.run(
            ["bash", str(root / ".claude/hooks/adr-gate.sh")],
            input=payload,
            capture_output=True,
            text=True,
            cwd=root,
        )

    def _abs(self, rel: str) -> str:
        top = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        return f"{top}/{rel}"

    def test_each_root_gated(self):
        for rel in ("src/app/w.py", "services/x/w.py"):
            r = self._run("src/app services", self._abs(rel))
            self.assertEqual(r.returncode, 0)
            self.assertIn("WidgetStore", r.stderr, rel)

    def test_relative_path(self):
        self.assertIn("WidgetStore", self._run("src/app services", "services/w.py").stderr)

    def test_outside_roots_silent(self):
        for rel in ("scripts/w.py", "vendor/services/w.py", "node_modules/x/services/w.py"):
            r = self._run("services", self._abs(rel))
            self.assertEqual(r.stderr, "", rel)

    def test_glob_chars_in_src_dir_not_expanded(self):
        r = self._run("*", self._abs("anything/w.py"))
        self.assertEqual(r.stderr, "")


# ------------------------------------------------------------------------------ statusline
@unittest.skipUnless(HAS_JQ, "statusline needs jq")
class Statusline(Base):
    def _run(self, payload, home: Path = None) -> subprocess.CompletedProcess:
        home = home or self.root / "home"
        home.mkdir(parents=True, exist_ok=True)
        return subprocess.run(
            ["bash", str(REPO / ".claude/statusline.sh")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=dict(os.environ, HOME=str(home)),
        )

    def _p(self, sid, pct, tok, **extra):
        return {
            "session_id": sid,
            "workspace": {"project_dir": "/x/myproj"},
            "context_window": {
                "used_percentage": pct,
                "total_input_tokens": tok,
                "total_output_tokens": 0,
            },
            **extra,
        }

    def test_model_and_mode(self):
        tr = self.root / "t.jsonl"
        tr.write_text('{"permissionMode":"default"}\n{"permissionMode":"acceptEdits"}\n')
        r = self._run(
            {
                "workspace": {"project_dir": "/x/myproj"},
                "model": {"display_name": "Opus"},
                "transcript_path": str(tr),
                "context_window": {
                    "used_percentage": 42.7,
                    "total_input_tokens": 1500,
                    "total_output_tokens": 500,
                },
            }
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("myproj | Opus accept | Ctx:42% | Tok:2K"), r.stdout)
        self.assertEqual(r.stdout.count("\n"), 1)

    def test_empty_input(self):
        r = self._run({})
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("Ctx:--"), r.stdout)
        self.assertEqual(r.stderr, "")

    def test_handoff_threshold_and_fast(self):
        r = self._run(
            {
                "model": {"display_name": "M"},
                "fast_mode": True,
                "context_window": {"used_percentage": 90},
            }
        )
        self.assertIn("M fast | !! CTX 90% HANDOFF", r.stdout)

    def test_weekly_counters(self):
        seq = [
            ("s1", 10, 200000),
            ("s1", 40, 410000),
            ("s1", 40, 410000),
            ("s1", 3, 60000),
            ("s1", 5, 80000),
            ("s2", 1, 10000),
        ]
        out = [self._run(self._p(*x)).stdout for x in seq]
        self.assertIn("Wk:200K | Win:1 Cmp:0", out[0])
        self.assertIn("Wk:410K | Win:1 Cmp:0", out[2])  # repeat render adds nothing
        self.assertIn("Wk:410K | Win:1 Cmp:1", out[3])  # compaction counted, no tokens added
        self.assertIn("Wk:440K | Win:2 Cmp:1", out[5])  # growth + new session

    def test_corrupt_state_is_harmless(self):
        home = self.root / "home"
        mk(home, {".claude/.weekly_state": "garbage\nx\n"})
        r = self._run(self._p("s", 5, 1000), home)
        self.assertEqual(r.stderr, "")
        self.assertIn("Ctx:5%", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
