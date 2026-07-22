"""
Detect technologies used in a cloned repo and return curated tutorial links.

Detection strategies:
1. File extensions → programming languages
2. Manifest files → frameworks, libraries, runtimes
3. Config files → developer tools
"""

import json
import re
from pathlib import Path

from config import CODE_EXTENSIONS, IGNORED_DIR_NAMES

TUTORIALS: dict[str, str] = {
    "Python": "https://docs.python.org/3/tutorial/",
    "JavaScript": "https://javascript.info/",
    "TypeScript": "https://www.typescriptlang.org/docs/handbook/",
    "Go": "https://go.dev/tour/",
    "Rust": "https://doc.rust-lang.org/book/",
    "Java": "https://docs.oracle.com/javase/tutorial/",
    "C": "https://learn.microsoft.com/en-us/cpp/c-language/",
    "C++": "https://www.learncpp.com/",
    "C#": "https://learn.microsoft.com/en-us/dotnet/csharp/",
    "Ruby": "https://ruby-doc.org/docs/ruby-doc-bundle/ProgrammingRuby/",
    "PHP": "https://www.php.net/manual/en/tutorial.php",
    "Swift": "https://docs.swift.org/swift-book/",
    "Kotlin": "https://kotlinlang.org/docs/home.html",
    "Scala": "https://docs.scala-lang.org/tour/tour-of-scala.html",
    "SQL": "https://www.sqltutorial.org/",
    "Shell": "https://www.gnu.org/software/bash/manual/",
    "React": "https://react.dev/learn",
    "Next.js": "https://nextjs.org/learn",
    "Vue.js": "https://vuejs.org/guide/introduction.html",
    "Angular": "https://angular.dev/overview",
    "Svelte": "https://svelte.dev/docs/introduction",
    "Django": "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
    "Flask": "https://flask.palletsprojects.com/en/stable/tutorial/",
    "FastAPI": "https://fastapi.tiangolo.com/tutorial/",
    "Express.js": "https://expressjs.com/en/starter/hello-world.html",
    "Node.js": "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs",
    "Docker": "https://docs.docker.com/get-started/",
    "PostgreSQL": "https://www.postgresql.org/docs/current/tutorial.html",
    "Redis": "https://redis.io/docs/get-started/",
    "MongoDB": "https://www.mongodb.com/docs/manual/tutorial/",
    "Tailwind CSS": "https://tailwindcss.com/docs",
    "Bootstrap": "https://getbootstrap.com/docs/5.3/getting-started/introduction/",
    "Prisma": "https://www.prisma.io/docs/getting-started",
    "GraphQL": "https://graphql.org/learn/",
    "WebSocket": "https://developer.mozilla.org/en-US/docs/Web/API/WebSocket",
    "GitHub Actions": "https://docs.github.com/en/actions",
    "Terraform": "https://developer.hashicorp.com/terraform/tutorials",
    "Kubernetes": "https://kubernetes.io/docs/tutorials/",
    "NumPy": "https://numpy.org/doc/stable/user/quickstart.html",
    "Pandas": "https://pandas.pydata.org/docs/getting_started/intro_tutorial.html",
    "TensorFlow": "https://www.tensorflow.org/tutorials",
    "PyTorch": "https://pytorch.org/tutorials/",
    "Flask": "https://flask.palletsprojects.com/en/stable/tutorial/",
    "Django REST Framework": "https://www.django-rest-framework.org/tutorial/quickstart/",
    "FastAPI": "https://fastapi.tiangolo.com/tutorial/",
    "Hono": "https://hono.dev/docs/getting-started/basic",
    "Deno": "https://docs.deno.com/runtime/manual/",
    "Bun": "https://bun.sh/docs",
}

MANIFEST_TECHS: list[tuple[str, list[str], str]] = [
    ("React", ["react"], "React"),
    ("Next.js", ["next"], "Next.js"),
    ("Vue.js", ["vue"], "Vue.js"),
    ("Angular", ["@angular/core"], "Angular"),
    ("Svelte", ["svelte"], "Svelte"),
    ("Express.js", ["express"], "Express.js"),
    ("FastAPI", ["fastapi"], "FastAPI"),
    ("Django", ["django"], "Django"),
    ("Flask", ["flask"], "Flask"),
    ("Django REST Framework", ["djangorestframework"], "Django REST Framework"),
    ("Hono", ["hono"], "Hono"),
    ("Tailwind CSS", ["tailwindcss"], "Tailwind CSS"),
    ("Bootstrap", ["bootstrap"], "Bootstrap"),
    ("Prisma", ["prisma", "@prisma/client"], "Prisma"),
    ("NumPy", ["numpy"], "NumPy"),
    ("Pandas", ["pandas"], "Pandas"),
    ("TensorFlow", ["tensorflow"], "TensorFlow"),
    ("PyTorch", ["torch"], "PyTorch"),
    ("Node.js", ["express", "fastify", "koa"], "Node.js"),
]

CONFIG_TECHS: list[tuple[str, str, str]] = [
    ("Dockerfile", "Docker"),
    ("docker-compose.yml", "Docker"),
    ("docker-compose.yaml", "Docker"),
    (".github", "GitHub Actions"),
    ("Makefile", "Make"),
    ("CMakeLists.txt", "CMake"),
    ("Cargo.toml", "Rust"),
    ("go.mod", "Go"),
    ("pom.xml", "Java (Maven)"),
    ("build.gradle", "Java (Gradle)"),
    ("Gemfile", "Ruby (Bundler)"),
    ("mix.exs", "Elixir"),
    ("pyproject.toml", "Python (pyproject)"),
    ("setup.py", "Python (setuptools)"),
    ("setup.cfg", "Python (setuptools)"),
    ("composer.json", "PHP (Composer)"),
    ("tsconfig.json", "TypeScript"),
    ("deno.json", "Deno"),
    ("bun.lockb", "Bun"),
    ("yarn.lock", "Yarn"),
    ("pnpm-lock.yaml", "pnpm"),
    ("package-lock.json", "npm"),
    ("terraform.tf", "Terraform"),
    ("nginx.conf", "Nginx"),
    (".eslintrc", "ESLint"),
    (".prettierrc", "Prettier"),
    ("jest.config", "Jest"),
    ("vitest.config", "Vitest"),
    ("pytest.ini", "Python (pytest)"),
    ("tox.ini", "Python (tox)"),
    (".travis.yml", "Travis CI"),
    ("Jenkinsfile", "Jenkins"),
    ("vercel.json", "Vercel"),
    ("netlify.toml", "Netlify"),
    ("fly.toml", "Fly.io"),
]

CONFIG_TECH_URLS: dict[str, str] = {
    "Docker": "https://docs.docker.com/get-started/",
    "GitHub Actions": "https://docs.github.com/en/actions",
    "Make": "https://www.gnu.org/software/make/manual/",
    "CMake": "https://cmake.org/cmake/help/latest/guide/tutorial/",
    "Rust": "https://doc.rust-lang.org/book/",
    "Go": "https://go.dev/tour/",
    "Java (Maven)": "https://maven.apache.org/guides/getting-started/",
    "Java (Gradle)": "https://docs.gradle.org/current/userguide/userguide.html",
    "Ruby (Bundler)": "https://bundler.io/guides/getting_started.html",
    "Elixir": "https://hexdocs.pm/elixir/introduction.html",
    "Python (pyproject)": "https://docs.python.org/3/library/distribution.html",
    "Python (setuptools)": "https://setuptools.pypa.io/en/latest/userguide/",
    "PHP (Composer)": "https://getcomposer.org/doc/00-intro.md",
    "TypeScript": "https://www.typescriptlang.org/docs/handbook/",
    "Deno": "https://docs.deno.com/runtime/manual/",
    "Bun": "https://bun.sh/docs",
    "Yarn": "https://yarnpkg.com/getting-started",
    "pnpm": "https://pnpm.io/getting-started",
    "npm": "https://docs.npmjs.com/cli/commands/npm",
    "Terraform": "https://developer.hashicorp.com/terraform/tutorials",
    "Nginx": "https://nginx.org/en/docs/",
    "ESLint": "https://eslint.org/docs/latest/user-guide/getting-started",
    "Prettier": "https://prettier.io/docs/en/index.html",
    "Jest": "https://jestjs.io/docs/getting-started",
    "Vitest": "https://vitest.dev/guide/",
    "Python (pytest)": "https://docs.pytest.org/en/stable/getting-started.html",
    "Python (tox)": "https://tox.wiki/en/stable/getting-started.html",
    "Travis CI": "https://docs.travis-ci.com/user/tutorial/",
    "Jenkins": "https://www.jenkins.io/doc/tutorials/",
    "Vercel": "https://vercel.com/docs",
    "Netlify": "https://docs.netlify.com/",
    "Fly.io": "https://fly.io/docs/hands-on/start/",
}


def detect_tech(repo_path: Path) -> list[dict]:
    """Scan a cloned repo and return a deduplicated list of {name, url} dicts."""
    seen: set[str] = set()
    results: list[dict] = []

    def _add(name: str, url: str | None = None) -> None:
        key = name.lower()
        if key in seen:
            return
        seen.add(key)
        results.append({"name": name, "url": url or TUTORIALS.get(name, "")})

    # 1. Languages from file extensions
    lang_counts: dict[str, int] = {}
    for path in repo_path.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORED_DIR_NAMES or part.startswith(".") for part in path.relative_to(repo_path).parts):
            continue
        lang = CODE_EXTENSIONS.get(path.suffix.lower())
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    for lang in sorted(lang_counts, key=lambda k: lang_counts[k], reverse=True):
        _add(lang)

    # 2. Manifest files → frameworks / libraries
    manifest_files = {
        "package.json": _parse_package_json,
        "requirements.txt": _parse_requirements_txt,
        "Pipfile": _parse_pipfile,
        "pyproject.toml": _parse_pyproject_toml,
        "go.mod": lambda p: [("Go", None)],
        "Cargo.toml": lambda p: [("Rust", None)],
    }

    for filename, parser in manifest_files.items():
        fpath = repo_path / filename
        if fpath.exists():
            try:
                for name, url in parser(fpath):
                    _add(name, url)
            except Exception:
                pass

    # 3. Config / tooling files
    for config_name, tech_name in CONFIG_TECHS:
        found = list(repo_path.glob(f"**/{config_name}"))
        if found:
            url = CONFIG_TECH_URLS.get(tech_name, TUTORIALS.get(tech_name, ""))
            _add(tech_name, url)

    return results


def _parse_package_json(path: Path) -> list[tuple[str, str | None]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return []
    deps = set(data.get("dependencies", {}).keys())
    dev_deps = set(data.get("devDependencies", {}).keys())
    all_deps = deps | dev_deps
    results = []
    for tech_name, packages, display_name in MANIFEST_TECHS:
        if any(p in all_deps for p in packages):
            url = TUTORIALS.get(display_name, "")
            results.append((display_name, url))
    return results


def _parse_requirements_txt(path: Path) -> list[tuple[str, str | None]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    deps = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = re.split(r"[>=<!~\[;]", line)[0].strip().lower().replace("-", "_")
        deps.add(name)
    results = []
    mapping = {
        "django": ("Django", None),
        "flask": ("Flask", None),
        "fastapi": ("FastAPI", None),
        "numpy": ("NumPy", None),
        "pandas": ("Pandas", None),
        "tensorflow": ("TensorFlow", None),
        "torch": ("PyTorch", None),
        "djangorestframework": ("Django REST Framework", None),
    }
    for pkg, info in mapping.items():
        if pkg in deps:
            results.append(info)
    return results


def _parse_pipfile(path: Path) -> list[tuple[str, str | None]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    deps = set()
    in_packages = False
    in_dev = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[packages]":
            in_packages = True
            in_dev = False
            continue
        if stripped == "[dev-packages]":
            in_packages = False
            in_dev = True
            continue
        if stripped.startswith("["):
            in_packages = False
            in_dev = False
            continue
        if (in_packages or in_dev) and stripped and not stripped.startswith("#"):
            name = re.split(r"[=]", stripped)[0].strip().lower().replace("-", "_")
            deps.add(name)
    results = []
    mapping = {
        "django": ("Django", None),
        "flask": ("Flask", None),
        "fastapi": ("FastAPI", None),
        "numpy": ("NumPy", None),
        "pandas": ("Pandas", None),
    }
    for pkg, info in mapping.items():
        if pkg in deps:
            results.append(info)
    return results


def _parse_pyproject_toml(path: Path) -> list[tuple[str, str | None]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    deps = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("[") and not stripped.startswith('"'):
            name = re.split(r"[>=<!~\[;]", stripped)[0].strip().strip('"').lower().replace("-", "_")
            if name and len(name) > 1:
                deps.add(name)
    results = []
    mapping = {
        "django": ("Django", None),
        "flask": ("Flask", None),
        "fastapi": ("FastAPI", None),
        "numpy": ("NumPy", None),
        "pandas": ("Pandas", None),
        "torch": ("PyTorch", None),
    }
    for pkg, info in mapping.items():
        if pkg in deps:
            results.append(info)
    return results
