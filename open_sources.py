import json
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree


OPEN_SOURCE_DIRNAME = ".open_sources"


def _get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Jarvis/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def _get_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Jarvis/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_")[:100] or "result"


def _write_result(directory: Path, source: str, title: str, metadata: dict, content: str) -> Path:
    path = directory / f"{source}_{_safe_name(title)}.txt"
    text = (
        f"Source: {source}\n"
        f"Title: {title}\n"
        f"Metadata: {json.dumps(metadata, ensure_ascii=False)}\n\n"
        f"{content.strip()}\n"
    )
    path.write_text(text, encoding="utf-8")
    return path


def collect_wikipedia(query: str, directory: Path, limit: int) -> int:
    data = _get_json(
        "https://en.wikipedia.org/w/rest.php/v1/search/page?q="
        f"{quote(query)}&limit={limit}"
    )
    count = 0
    for item in data.get("pages", []):
        title = item.get("title", "Wikipedia result")
        metadata = {"id": item.get("id"), "description": item.get("description"), "source_url": item.get("key")}
        content = f"{item.get('description', '')}\n{item.get('excerpt', '')}"
        _write_result(directory, "wikipedia", title, metadata, content)
        count += 1
    return count


def collect_arxiv(query: str, directory: Path, limit: int) -> int:
    xml = _get_text(
        "https://export.arxiv.org/api/query?search_query=all:"
        f"{quote(query)}&start=0&max_results={limit}"
    )
    root = ElementTree.fromstring(xml)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    count = 0
    for entry in root.findall("atom:entry", namespace):
        title = " ".join((entry.findtext("atom:title", "", namespace) or "").split())
        summary = " ".join((entry.findtext("atom:summary", "", namespace) or "").split())
        link = entry.findtext("atom:id", "", namespace)
        authors = [author.findtext("atom:name", "", namespace) for author in entry.findall("atom:author", namespace)]
        metadata = {"source_url": link, "published": entry.findtext("atom:published", "", namespace), "authors": authors}
        _write_result(directory, "arxiv", title, metadata, summary)
        count += 1
    return count


def collect_gutenberg(query: str, directory: Path, limit: int) -> int:
    data = _get_json(f"https://gutendex.com/books/?search={quote(query)}")
    count = 0
    for item in data.get("results", [])[:limit]:
        title = item.get("title", "Gutenberg result")
        metadata = {
            "id": item.get("id"),
            "authors": item.get("authors"),
            "subjects": item.get("subjects"),
            "source_url": f"https://www.gutenberg.org/ebooks/{item.get('id')}",
        }
        content = f"Authors: {item.get('authors')}\nSubjects: {item.get('subjects')}\nFormats: {item.get('formats')}"
        _write_result(directory, "gutenberg", title, metadata, content)
        count += 1
    return count


def collect_government(query: str, directory: Path, limit: int) -> int:
    data = _get_json(f"https://api.us.socrata.com/api/catalog/v1?q={quote(query)}&limit={limit}")
    count = 0
    for result in data.get("results", []):
        resource = result.get("resource", {})
        metadata = {
            "domain": result.get("metadata", {}).get("domain"),
            "resource_id": resource.get("id"),
            "format": resource.get("format"),
            "source_url": resource.get("url"),
        }
        _write_result(directory, "government", resource.get("name", "Government dataset"), metadata, resource.get("description", ""))
        count += 1
    return count


def collect_open_sources(documents_dir: Path, query: str, limit: int = 5) -> int:
    directory = documents_dir / OPEN_SOURCE_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    collectors = {
        "Wikipedia": collect_wikipedia,
        "arXiv": collect_arxiv,
        "Project Gutenberg": collect_gutenberg,
        "Government data": collect_government,
    }
    total = 0
    for label, collector in collectors.items():
        try:
            count = collector(query, directory, limit)
            print(f"{label}: collected {count} result(s)")
            total += count
        except (OSError, ValueError, ElementTree.ParseError) as error:
            print(f"{label}: collection failed: {error}")
    return total
