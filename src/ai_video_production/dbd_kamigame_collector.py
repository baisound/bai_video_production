"""Kamigame DbD knowledge candidate collector.

Kamigame is treated as COMMUNITY_REFERENCE only. Scraped material is stored as
raw snapshots plus reviewable candidate records and is never auto-promoted to
VERIFIED canonical game knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import csv
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso

SURVIVOR_PERKS_URL = "https://kamigame.jp/dbd/page/207150682694767780.html"
KILLER_PERKS_URL = "https://kamigame.jp/dbd/page/207148601481152853.html"
KILLERS_URL = "https://kamigame.jp/dbd/page/93384114123571207.html"
_ALLOWED_PAGE_HOSTS = {"kamigame.jp", "www.kamigame.jp"}
_NEXT_TEXT = {"次へ", "次のページ", "次", ">", "›", "»"}
_WS_RE = re.compile(r"\s+")
_STARS_RE = re.compile(r"[★☆]+")
_SPEED_RE = re.compile(r"移動速度[：:]\s*([^\s]+)")
_RADIUS_RE = re.compile(r"脅威範囲[：:]\s*([^\s]+)")
_HEIGHT_RE = re.compile(r"背の高さ[：:]\s*([^\s|]+)")


@dataclass(slots=True)
class Link:
    text: str
    href: str


@dataclass(slots=True)
class Cell:
    text_parts: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    images: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self.text_parts))


@dataclass(slots=True)
class Row:
    cells: list[Cell] = field(default_factory=list)


class _KamigameHTMLParser(HTMLParser):
    def __init__(self, *, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.rows: list[Row] = []
        self.links: list[Link] = []
        self.images: list[str] = []
        self.headings: list[tuple[str, str]] = []
        self._row: Row | None = None
        self._cell: Cell | None = None
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self._heading_tag: str | None = None
        self._heading_text: list[str] = []
        self._all_text: list[str] = []

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self._all_text))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v for k, v in attrs}
        if tag == "tr":
            self._row = Row()
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = Cell()
        elif tag == "a":
            href = attr.get("href")
            self._anchor_href = urljoin(self.base_url, href) if href else None
            self._anchor_text = []
        elif tag == "img":
            src = attr.get("src") or attr.get("data-src") or attr.get("data-original")
            if src:
                absolute = urljoin(self.base_url, src)
                self.images.append(absolute)
                if self._cell is not None:
                    self._cell.images.append(absolute)
        elif tag in {"h1", "h2", "h3", "h4"}:
            self._heading_tag = tag
            self._heading_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.cells.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row.cells:
                self.rows.append(self._row)
            self._row = None
        elif tag == "a" and self._anchor_href:
            link = Link(_clean_text(" ".join(self._anchor_text)), self._anchor_href)
            self.links.append(link)
            if self._cell is not None:
                self._cell.links.append(link)
            self._anchor_href = None
            self._anchor_text = []
        elif tag == self._heading_tag:
            text = _clean_text(" ".join(self._heading_text))
            if text:
                self.headings.append((tag, text))
            self._heading_tag = None
            self._heading_text = []

    def handle_data(self, data: str) -> None:
        if not data or not data.strip():
            return
        text = data.strip()
        self._all_text.append(text)
        if self._cell is not None:
            self._cell.text_parts.append(text)
        if self._anchor_href is not None:
            self._anchor_text.append(text)
        if self._heading_tag is not None:
            self._heading_text.append(text)


def _clean_text(value: str) -> str:
    return _WS_RE.sub(" ", value.replace("\u3000", " ")).strip()


def _stable_candidate_id(prefix: str, name: str) -> str:
    return f"{prefix}_kamigame_{hashlib.sha256(name.encode('utf-8')).hexdigest()[:16]}"


def _source_id(url: str, content_sha256: str) -> str:
    digest = hashlib.sha256(f"{url}\n{content_sha256}".encode("utf-8")).hexdigest()[:20]
    return f"src_kamigame_{digest}"


def _same_kamigame_page(url: str) -> bool:
    p = urlparse(url)
    return p.scheme in {"http", "https"} and p.hostname in _ALLOWED_PAGE_HOSTS and p.path.startswith("/dbd/")


def _aliases(name: str, cell: Cell) -> list[str]:
    values: list[str] = []
    for link in cell.links[1:]:
        v = link.text.strip().strip("()（）")
        if v and v != name and len(v) <= 96:
            values.append(v)
    for match in re.findall(r"[（(]([^()（）]{1,96})[）)]", cell.text):
        v = _clean_text(match)
        if v and v != name:
            values.append(v)
    return list(dict.fromkeys(values))


def _effect(text: str) -> str:
    if "〖効果〗" not in text:
        return ""
    value = text.split("〖効果〗", 1)[1]
    if "〖一致するカテゴリ〗" in value:
        value = value.split("〖一致するカテゴリ〗", 1)[0]
    return _clean_text(value)


def _owner(cell: Cell) -> str | None:
    if "所有者" not in cell.text:
        return None
    return cell.links[0].text if cell.links else None


def parse_perk_page(html_text: str, *, page_url: str, role: str) -> list[dict[str, object]]:
    parser = _KamigameHTMLParser(base_url=page_url); parser.feed(html_text)
    records: list[dict[str, object]] = []; seen: set[tuple[str, str]] = set()
    for row in parser.rows:
        if len(row.cells) < 2:
            continue
        name_cell, detail = row.cells[0], row.cells[1]
        if not name_cell.links or "効果" not in detail.text:
            continue
        name = _clean_text(name_cell.links[0].text or name_cell.text)
        if not name or name in {"パーク", "詳細"} or (role, name) in seen:
            continue
        seen.add((role, name))
        owner = _owner(detail)
        stars = _STARS_RE.search(detail.text)
        records.append({
            "schema_version": "1.0.0", "record_kind": "PERK_CANDIDATE",
            "candidate_id": _stable_candidate_id("perk", f"{role}:{name}"), "canonical_perk_id": None,
            "role": role, "name_ja": name, "aliases_ja": _aliases(name, name_cell), "owner_name_ja": owner,
            "priority": stars.group(0).count("★") if stars else None,
            "source_effect_ja": _effect(detail.text),
            "source_categories_ja": list(dict.fromkeys(link.text for link in detail.links if link.text and link.text != owner)) if "一致するカテゴリ" in detail.text else [],
            "detail_url": name_cell.links[0].href if _same_kamigame_page(name_cell.links[0].href) else page_url,
            "image_urls": list(dict.fromkeys(name_cell.images)), "review_status": "CANDIDATE",
            "source_authority": "COMMUNITY_REFERENCE", "source_page_url": page_url,
        })
    return records


def parse_killer_list_page(html_text: str, *, page_url: str) -> list[dict[str, object]]:
    parser = _KamigameHTMLParser(base_url=page_url); parser.feed(html_text)
    records: list[dict[str, object]] = []; seen: set[str] = set()
    for row in parser.rows:
        if len(row.cells) < 3:
            continue
        name_cell, stats, perks = row.cells[:3]
        if not name_cell.links or "移動速度" not in stats.text:
            continue
        name = _clean_text(name_cell.links[0].text or name_cell.text)
        if not name or name in seen:
            continue
        seen.add(name)
        speed, radius, height = _SPEED_RE.search(stats.text), _RADIUS_RE.search(stats.text), _HEIGHT_RE.search(stats.text)
        detail_url = name_cell.links[0].href
        records.append({
            "schema_version": "1.0.0", "record_kind": "KILLER_CANDIDATE",
            "candidate_id": _stable_candidate_id("killer", name), "canonical_killer_id": None, "name_ja": name,
            "movement_speed_text": speed.group(1) if speed else None,
            "terror_radius_text": radius.group(1) if radius else None,
            "height_text": _clean_text(height.group(1)) if height else None,
            "unique_perks_ja": [link.text for link in perks.links if link.text],
            "detail_url": detail_url if _same_kamigame_page(detail_url) else None,
            "image_urls": list(dict.fromkeys(name_cell.images)), "review_status": "CANDIDATE",
            "source_authority": "COMMUNITY_REFERENCE", "source_page_url": page_url,
        })
    return records


def parse_killer_detail_page(html_text: str, *, page_url: str) -> dict[str, object]:
    parser = _KamigameHTMLParser(base_url=page_url); parser.feed(html_text)
    headings = [text for _, text in parser.headings]
    return {
        "page_url": page_url, "headings": headings[:128],
        "contains_power_section": any(any(term in h for term in ("特殊能力", "能力", "パワー")) for h in headings),
        "contains_addon_section": any("アドオン" in h for h in headings),
        "page_text_excerpt": parser.text[:12000],
        "image_urls": list(dict.fromkeys(parser.images))[:256],
        "linked_dbd_pages": [link.href for link in parser.links if _same_kamigame_page(link.href)][:512],
    }


def discover_next_pages(html_text: str, *, page_url: str) -> list[str]:
    parser = _KamigameHTMLParser(base_url=page_url); parser.feed(html_text)
    current = urlparse(page_url); result: list[str] = []
    for link in parser.links:
        p = urlparse(link.href)
        if p.hostname not in _ALLOWED_PAGE_HOSTS or p.path != current.path:
            continue
        query = p.query.casefold(); text = _clean_text(link.text)
        if text in _NEXT_TEXT or "次" in text or any(token in query for token in ("page=", "p=", "offset=")):
            if link.href != page_url and link.href not in result:
                result.append(link.href)
    return result


@dataclass(slots=True)
class FetchReceipt:
    url: str; path: Path; content_sha256: str; retrieved_at: str; content_type: str


class KamigameHTTPClient:
    def __init__(self, *, timeout_seconds: float = 20.0, minimum_delay_seconds: float = 0.75, user_agent: str = "BAI-Video-Production-DbD-Knowledge-Collector/1.0") -> None:
        self.timeout_seconds = timeout_seconds; self.minimum_delay_seconds = minimum_delay_seconds; self.user_agent = user_agent; self._last_request_at = 0.0

    def fetch_html(self, url: str, *, output_path: Path) -> FetchReceipt:
        if not _same_kamigame_page(url):
            raise ValueError("collector URL must remain under kamigame.jp/dbd/")
        delay = self.minimum_delay_seconds - (time.monotonic() - self._last_request_at)
        if delay > 0: time.sleep(delay)
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"})
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - allow-listed domain
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}: raise ValueError(f"unexpected content type: {content_type}")
            body = response.read(8 * 1024 * 1024 + 1)
            if len(body) > 8 * 1024 * 1024: raise ValueError("page exceeds 8 MiB safety limit")
        self._last_request_at = time.monotonic(); output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_bytes(body)
        return FetchReceipt(url, output_path, hashlib.sha256(body).hexdigest(), utc_now_iso(), content_type)


def _write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> int:
    rows = list(rows); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as h:
        for row in rows: h.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return len(rows)


def _dedupe(records: Iterable[dict[str, object]], key: str) -> list[dict[str, object]]:
    items = {str(record[key]): record for record in records}; return [items[k] for k in sorted(items)]


class KamigameDbDKnowledgeCollector:
    def __init__(self, output_root: str | Path, *, client: KamigameHTTPClient | None = None) -> None:
        self.output_root = Path(output_root); self.client = client or KamigameHTTPClient(); self.raw_root = self.output_root / "raw"; self.normalized_root = self.output_root / "normalized"

    def _crawl_list(self, start_url: str, *, kind: str, max_pages: int) -> tuple[list[dict[str, object]], list[FetchReceipt]]:
        pending=[start_url]; visited:set[str]=set(); receipts:list[FetchReceipt]=[]; records:list[dict[str, object]]=[]
        while pending and len(visited)<max_pages:
            url=pending.pop(0)
            if url in visited: continue
            visited.add(url); raw=self.raw_root/kind/f"page-{len(visited):03d}.html"; receipt=self.client.fetch_html(url, output_path=raw); receipts.append(receipt)
            text=raw.read_text(encoding="utf-8", errors="replace")
            if kind=="survivor-perks": records.extend(parse_perk_page(text,page_url=url,role="SURVIVOR"))
            elif kind=="killer-perks": records.extend(parse_perk_page(text,page_url=url,role="KILLER"))
            else: records.extend(parse_killer_list_page(text,page_url=url))
            for nxt in discover_next_pages(text,page_url=url):
                if nxt not in visited and nxt not in pending: pending.append(nxt)
        return records,receipts

    def collect(self, *, follow_killer_details: bool=True, max_pages: int=20, max_killer_details: int=128) -> dict[str, object]:
        self.output_root.mkdir(parents=True, exist_ok=True)
        survivor, rs=self._crawl_list(SURVIVOR_PERKS_URL,kind="survivor-perks",max_pages=max_pages)
        killer_perks, rkp=self._crawl_list(KILLER_PERKS_URL,kind="killer-perks",max_pages=max_pages)
        killers, rk=self._crawl_list(KILLERS_URL,kind="killers",max_pages=max_pages)
        details={}; rd=[]
        if follow_killer_details:
            for i,killer in enumerate(killers[:max_killer_details],1):
                url=killer.get("detail_url")
                if not isinstance(url,str) or not url: continue
                raw=self.raw_root/"killer-details"/f"{i:03d}-{killer['candidate_id']}.html"; receipt=self.client.fetch_html(url,output_path=raw); rd.append(receipt)
                details[str(killer["candidate_id"])]=parse_killer_detail_page(raw.read_text(encoding="utf-8",errors="replace"),page_url=url)
        survivor=_dedupe(survivor,"candidate_id"); killer_perks=_dedupe(killer_perks,"candidate_id"); killers=_dedupe(killers,"candidate_id")
        for killer in killers:
            if str(killer["candidate_id"]) in details: killer["detail"]=details[str(killer["candidate_id"])]
        _write_jsonl(self.normalized_root/"survivor-perks.jsonl",survivor); _write_jsonl(self.normalized_root/"killer-perks.jsonl",killer_perks); _write_jsonl(self.normalized_root/"killers.jsonl",killers)
        sources=[]
        for r in [*rs,*rkp,*rk,*rd]:
            sources.append({"schema_version":"1.0.0","source_id":_source_id(r.url,r.content_sha256),"source_type":"KAMIGAME_HTML","authority":"COMMUNITY_REFERENCE","url":r.url,"retrieved_at":r.retrieved_at,"content_sha256":r.content_sha256,"raw_path":r.path.relative_to(self.output_root).as_posix(),"locale":"ja-JP"})
        sources=_dedupe(sources,"source_id"); _write_jsonl(self.normalized_root/"sources.jsonl",sources)
        aliases=self.normalized_root/"aliases.csv"; aliases.parent.mkdir(parents=True,exist_ok=True)
        with aliases.open("w",encoding="utf-8-sig",newline="") as h:
            w=csv.writer(h); w.writerow(["record_kind","candidate_id","canonical_id","locale","alias","review_status"])
            for record in [*survivor,*killer_perks]:
                for alias in record.get("aliases_ja",[]): w.writerow(["PERK",record["candidate_id"],"","ja-JP",alias,"CANDIDATE"])
            for record in killers: w.writerow(["KILLER",record["candidate_id"],"","ja-JP",record["name_ja"],"CANDIDATE"])
        body={"schema_version":"1.0.0","collector":"KAMIGAME_DBD_KNOWLEDGE","generated_at":utc_now_iso(),"authority":"COMMUNITY_REFERENCE","automatic_verification":False,"canonical_write_performed":False,"source_urls":[SURVIVOR_PERKS_URL,KILLER_PERKS_URL,KILLERS_URL],"counts":{"survivor_perks":len(survivor),"killer_perks":len(killer_perks),"killers":len(killers),"killer_details":len(details),"source_snapshots":len(sources)},"outputs":{"survivor_perks":"normalized/survivor-perks.jsonl","killer_perks":"normalized/killer-perks.jsonl","killers":"normalized/killers.jsonl","aliases":"normalized/aliases.csv","sources":"normalized/sources.jsonl"}}
        manifest={**body,"manifest_sha256":sha256_bytes(canonical_json_bytes(body))}; (self.output_root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return manifest
