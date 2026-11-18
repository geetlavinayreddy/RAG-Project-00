import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".docx"}
MAX_FILE_SIZES = {
    ".pdf": 50 * 1024 * 1024,
    ".txt": 10 * 1024 * 1024,
    ".md": 10 * 1024 * 1024,
    ".csv": 25 * 1024 * 1024,
    ".json": 25 * 1024 * 1024,
    ".docx": 50 * 1024 * 1024,
}
SKIPPED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    "target",
    "venv",
    ".venv",
    "chroma_db",
}
SKIPPED_NAMES = {
    ".env",
    "package-lock.json",
    "package.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "gradle.lockfile",
    "firebase-applet-config.json",
    "requirements.txt",
    "tsconfig.json",
    "vercel.json",
}


def discover_repositories(owner: str) -> list[dict]:
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                owner,
                "--limit",
                "1000",
                "--json",
                "name,url,isArchived,isPrivate",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        repos = json.loads(result.stdout)
        return [
            {
                "name": repo["name"],
                "clone_url": f"{repo['url'].rstrip('/')}.git",
                "private": repo["isPrivate"],
            }
            for repo in repos
            if not repo["isArchived"]
        ]
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    repositories = []
    page = 1
    while True:
        url = (
            "https://api.github.com/users/"
            f"{quote(owner, safe='')}/repos?per_page=100&page={page}&sort=updated"
        )
        request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Jarvis/1.0"})
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not batch:
            break
        repositories.extend(
            {"name": repo["name"], "clone_url": repo["clone_url"], "private": repo["private"]}
            for repo in batch
            if not repo["archived"]
        )
        if len(batch) < 100:
            break
        page += 1
    return repositories


def _allowed_file(path: Path) -> bool:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False
    if any(part.lower() in SKIPPED_DIRECTORIES for part in path.parts):
        return False
    name = path.name.lower()
    if name in SKIPPED_NAMES:
        return False
    if name.startswith(".env") or name.endswith(".lock"):
        return False
    try:
        return path.stat().st_size <= MAX_FILE_SIZES[path.suffix.lower()]
    except OSError:
        return False


def _repo_head(repository_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def collect_github_repositories(
    documents_dir: Path,
    owner: str,
    timeout: int = 120,
) -> dict:
    destination = documents_dir / ".github_repositories"
    destination.mkdir(parents=True, exist_ok=True)
    repositories = discover_repositories(owner)
    manifest_path = destination / "repository_manifest.json"
    imported: list[dict] = []
    duplicates: list[dict] = []
    failed: list[dict] = []
    seen_hashes: dict[str, str] = {}

    for repository in repositories:
        name = repository["name"]
        repo_destination = destination / name
        if repo_destination.exists():
            shutil.rmtree(repo_destination)
        with tempfile.TemporaryDirectory(prefix="jarvis_repo_") as temp:
            repo_dir = Path(temp) / name
            try:
                if repository["private"]:
                    subprocess.run(
                        [
                            "gh",
                            "repo",
                            "clone",
                            f"{owner}/{name}",
                            str(repo_dir),
                            "--",
                            "--depth",
                            "1",
                        ],
                        check=True,
                        capture_output=True,
                        timeout=timeout,
                    )
                else:
                    subprocess.run(
                        ["git", "clone", "--depth", "1", "--quiet", repository["clone_url"], str(repo_dir)],
                        check=True,
                        capture_output=True,
                        timeout=timeout,
                    )
                commit = _repo_head(repo_dir)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                failed.append({"repository": name, "error": str(error)})
                continue

            for path in sorted(repo_dir.rglob("*")):
                if not path.is_file() or not _allowed_file(path):
                    continue
                try:
                    content = path.read_bytes()
                except OSError as error:
                    failed.append({"repository": name, "path": str(path.relative_to(repo_dir)), "error": str(error)})
                    continue
                digest = hashlib.sha256(content).hexdigest()
                relative = path.relative_to(repo_dir).as_posix()
                record = {
                    "repository": f"{owner}/{name}",
                    "commit": commit,
                    "path": relative,
                    "url": f"https://github.com/{owner}/{name}/blob/{commit}/{quote(relative, safe='/')}",
                    "sha256": digest,
                    "bytes": len(content),
                }
                if digest in seen_hashes:
                    duplicates.append({**record, "duplicate_of": seen_hashes[digest]})
                    continue
                target = repo_destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                seen_hashes[digest] = f"{owner}/{name}/{relative}"
                imported.append(record)

    stale_repositories = {
        path.name for path in destination.iterdir()
        if path.is_dir() and path.name not in {repo["name"] for repo in repositories}
    }
    for name in stale_repositories:
        shutil.rmtree(destination / name)

    manifest = {
        "owner": owner,
        "repositories": repositories,
        "imported": imported,
        "duplicates": duplicates,
        "failed": failed,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
