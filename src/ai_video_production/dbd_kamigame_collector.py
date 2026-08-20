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
import shutil
import time
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .serialization import canonical_json_bytes, sha256_bytes, utc_now_iso

SURVIVOR_PERKS_URL = "https://kamigame.jp/dbd/page/207150682694767780.html"
KILLER_PERKS_URL = "https://kamigame.jp/dbd/page/207148601481152853.html"
KILLERS_URL = "https://kamigame.jp/dbd/page/93384114123571207.html"
ITEMS_URL = "https://kamigame.jp/dbd/page/94107608092246023.html"
ADDONS_URL = "https://kamigame.jp/dbd/page/93674768519135239.html"
MAPS_URL = "https://kamigame.jp/dbd/page/94254357779841031.html"
_ALLOWED_PAGE_HOSTS = {"kamigame.jp", "www.kamigame.jp"}
_ALLOWED_ASSET_HOST_SUFFIXES = ("kamigame.jp", ".googleusercontent.com", ".googleapis.com")
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
    section_heading: str = ""


@dataclass(slots=True)
class _ElementFrame:
    tag: str
    attributes: dict[str, str]
    in_article_root: bool
    excluded: bool
    terminal: bool


def _row_source_sections(row: Row) -> list[dict[str, object]]:
    """Preserve source fields that do not yet have a dedicated normalized column."""
    sections: list[dict[str, object]] = []
    for index, cell in enumerate(row.cells, start=1):
        value = cell.text
        if not value:
            continue
        sections.append({
            "heading": row.section_heading,
            "label": f"列{index}",
            "value": value[:12000],
            "order": index,
        })
    return sections


class _KamigameHTMLParser(HTMLParser):
    _VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, *, base_url: str, article_scope: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.article_scope = article_scope
        self.rows: list[Row] = []
        self.links: list[Link] = []
        self.images: list[str] = []
        self.section_images: list[tuple[str, str]] = []
        self.headings: list[tuple[str, str]] = []
        self._row: Row | None = None
        self._cell: Cell | None = None
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self._heading_tag: str | None = None
        self._heading_text: list[str] = []
        self._all_text: list[str] = []
        self._current_heading: str = ""
        self._stack: list[_ElementFrame] = []
        self._article_root_seen = False
        self._article_h1_seen = False
        self._terminal_reached = False

    @property
    def template_id(self) -> str:
        if self._article_root_seen and self._article_h1_seen:
            return "KAMIGAME_ARTICLE_MAIN_V1"
        return "UNKNOWN"

    @property
    def structure_status(self) -> str:
        return "ACCEPTED" if self.template_id != "UNKNOWN" else "UNKNOWN_STRUCTURE"

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self._all_text))

    @staticmethod
    def _attributes(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {str(key).casefold(): str(value or "") for key, value in attrs}

    @staticmethod
    def _class_tokens(attributes: dict[str, str]) -> set[str]:
        return {
            token.casefold()
            for token in re.split(r"\s+", attributes.get("class", "").strip())
            if token
        }

    @classmethod
    def _structurally_excluded(cls, tag: str, attributes: dict[str, str]) -> bool:
        if tag in {"aside", "nav", "footer"}:
            return True
        tokens = cls._class_tokens(attributes)
        element_id = attributes.get("id", "").casefold()
        markers = {*tokens, element_id}
        return any(
            marker == "ad"
            or marker.startswith("ad_")
            or marker.endswith("_ad")
            or marker.startswith("inline_ad")
            or marker.startswith("related")
            or marker.startswith("relation")
            or marker.startswith("recommend")
            or marker.startswith("ranking")
            or marker.endswith("_navigation")
            or marker in {
                "information_footer",
                "priority_side",
                "sidebar",
                "ranking",
                "recommendation",
                "navigation",
            }
            for marker in markers
            if marker
        )

    def _frame_for_start(self, tag: str, attributes: dict[str, str]) -> _ElementFrame:
        parent = self._stack[-1] if self._stack else None
        parent_is_main = bool(
            parent
            and parent.tag == "main"
            and parent.attributes.get("id", "").casefold() == "main"
            and "article" in self._class_tokens(parent.attributes)
        )
        is_article_root = tag == "article" and parent_is_main
        if is_article_root:
            self._article_root_seen = True
        in_root = bool(is_article_root or (parent and parent.in_article_root))
        excluded = bool(
            (parent and parent.excluded)
            or (in_root and self._structurally_excluded(tag, attributes))
        )
        terminal = bool((parent and parent.terminal) or self._terminal_reached)
        if (
            in_root
            and not excluded
            and tag == "h2"
            and attributes.get("id", "").strip() in {"関連リンク", "related-links"}
        ):
            self._terminal_reached = True
            terminal = True
        return _ElementFrame(tag, attributes, in_root, excluded, terminal)

    def _capture_allowed(self, frame: _ElementFrame | None = None) -> bool:
        if not self.article_scope:
            return True
        current = frame or (self._stack[-1] if self._stack else None)
        return bool(
            current
            and current.in_article_root
            and not current.excluded
            and not current.terminal
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attr = self._attributes(attrs)
        frame = self._frame_for_start(tag, attr)
        if tag not in self._VOID_TAGS:
            self._stack.append(frame)
        if not self._capture_allowed(frame):
            return
        if tag == "tr":
            self._row = Row(section_heading=self._current_heading)
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
                self.section_images.append((self._current_heading, absolute))
                if self._cell is not None:
                    self._cell.images.append(absolute)
        elif tag in {"h1", "h2", "h3", "h4"}:
            self._heading_tag = tag
            self._heading_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if self._capture_allowed():
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
                    self._current_heading = text
                    if tag == "h1" and self.article_scope:
                        self._article_h1_seen = True
                self._heading_tag = None
                self._heading_text = []
        if tag not in self._VOID_TAGS:
            for index in range(len(self._stack) - 1, -1, -1):
                if self._stack[index].tag == tag:
                    del self._stack[index:]
                    break

    def handle_data(self, data: str) -> None:
        if not data or not data.strip() or not self._capture_allowed():
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
    effect_marker = next((marker for marker in ("【効果】", "〖効果〗") if marker in text), None)
    if effect_marker is None:
        return ""
    value = text.split(effect_marker, 1)[1]
    category_marker = next(
        (marker for marker in ("【一致するカテゴリ】", "〖一致するカテゴリ〗") if marker in value),
        None,
    )
    if category_marker is not None:
        value = value.split(category_marker, 1)[0]
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
            "source_authority": "COMMUNITY_REFERENCE", "source_section_heading": row.section_heading, "source_sections": _row_source_sections(row), "source_page_url": page_url,
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
            "source_authority": "COMMUNITY_REFERENCE", "source_section_heading": row.section_heading, "source_sections": _row_source_sections(row), "source_page_url": page_url,
        })
    return records


def parse_killer_detail_page(html_text: str, *, page_url: str) -> dict[str, object]:
    parser = _KamigameHTMLParser(base_url=page_url, article_scope=True); parser.feed(html_text)
    if parser.structure_status != "ACCEPTED":
        return {
            "page_url": page_url,
            "template_id": "UNKNOWN",
            "structure_status": "UNKNOWN_STRUCTURE",
            "requires_human_review": True,
            "headings": [],
            "detail_sections": [],
            "contains_power_section": False,
            "contains_addon_section": False,
            "page_text_excerpt": "",
            "image_urls": [],
            "linked_dbd_pages": [],
        }
    headings = [text for _, text in parser.headings]
    section_kinds: list[dict[str, str]] = []
    for level, heading in parser.headings:
        if level == "h1":
            continue
        if any(term in heading for term in ("ステータス", "基本情報")):
            section_kind = "ENTITY_STAT_TABLE"
        elif "固有パーク" in heading:
            section_kind = "UNIQUE_PERK_SECTION"
        elif "アドオン" in heading and any(term in heading for term in ("評価", "おすすめ")):
            section_kind = "ADDON_EVALUATION_SECTION"
        elif any(term in heading for term in ("評価", "強さ")):
            section_kind = "EVALUATION_SECTION"
        elif any(term in heading for term in ("能力", "パワー")):
            section_kind = "ENTITY_FACT_SECTION"
        elif any(term in heading for term in ("使い方", "立ち回り", "対策")):
            section_kind = "TACTICAL_TEXT"
        else:
            section_kind = "UNKNOWN_SECTION"
        section_kinds.append({"heading_level": level, "heading": heading, "section_kind": section_kind})
    return {
        "page_url": page_url,
        "template_id": parser.template_id,
        "structure_status": parser.structure_status,
        "requires_human_review": False,
        "headings": headings[:128],
        "detail_sections": section_kinds[:128],
        "contains_power_section": any(row["section_kind"] == "ENTITY_FACT_SECTION" for row in section_kinds),
        "contains_addon_section": any(row["section_kind"] == "ADDON_EVALUATION_SECTION" for row in section_kinds),
        "page_text_excerpt": parser.text[:12000],
        "image_urls": list(dict.fromkeys(parser.images))[:256],
        "linked_dbd_pages": [link.href for link in parser.links if _same_kamigame_page(link.href)][:512],
    }




def _first_name_and_image(cell: Cell) -> tuple[str, list[str], str | None]:
    name = ""
    detail_url: str | None = None
    if cell.links:
        name = _clean_text(cell.links[0].text)
        detail_url = cell.links[0].href if _same_kamigame_page(cell.links[0].href) else None
    if not name:
        name = cell.text.split(" ", 1)[0].strip()
    return name, list(dict.fromkeys(cell.images)), detail_url


def _parse_rarity(text: str) -> str:
    for value in ("Ultra Rare", "Very Rare", "Rare", "Uncommon", "Common", "common", "event"):
        if value in text:
            return value
    return ""


def _section_key(text: str) -> str:
    value = _clean_text(text)
    value = re.sub(r"一覧.*$", "", value).strip()
    value = re.sub(r"系アイテム.*$", "", value).strip()
    value = re.sub(r"の?アドオン$", "", value).strip()
    return value


def parse_item_page(html_text: str, *, page_url: str) -> list[dict[str, object]]:
    parser = _KamigameHTMLParser(base_url=page_url); parser.feed(html_text)
    rows: list[dict[str, object]] = []; seen: set[str] = set()
    for row in parser.rows:
        if len(row.cells) < 2:
            continue
        name_cell, detail = row.cells[0], row.cells[1]
        if "効果" not in detail.text and "基礎チャージ" not in detail.text:
            continue
        name, images, detail_url = _first_name_and_image(name_cell)
        if not name or name in {"アイテム", "性能"} or name in seen:
            continue
        seen.add(name)
        charge = ""
        m = re.search(r"基礎チャージ量[〗】]?\s*([0-9]+(?:秒)?)", detail.text)
        if m: charge = m.group(1)
        rows.append({
            "schema_version": "1.0.0", "record_kind": "ITEM_CANDIDATE",
            "candidate_id": _stable_candidate_id("item", name), "canonical_item_id": None,
            "name_ja": name, "aliases_ja": _aliases(name, name_cell),
            "category_ja": _section_key(row.section_heading),
            "rarity": _parse_rarity(detail.text), "base_charges_text": charge,
            "source_effect_ja": _effect(detail.text),
            "detail_url": detail_url, "image_urls": images,
            "review_status": "CANDIDATE", "source_authority": "COMMUNITY_REFERENCE",
            "source_section_heading": row.section_heading, "source_sections": _row_source_sections(row), "source_page_url": page_url,
        })
    return rows


def parse_addon_page(html_text: str, *, page_url: str) -> list[dict[str, object]]:
    parser = _KamigameHTMLParser(base_url=page_url); parser.feed(html_text)
    rows: list[dict[str, object]] = []; seen: set[tuple[str, str]] = set()
    for row in parser.rows:
        if len(row.cells) < 2:
            continue
        name_cell, detail = row.cells[0], row.cells[1]
        if "効果" not in detail.text and not name_cell.images:
            continue
        name, images, detail_url = _first_name_and_image(name_cell)
        owner = _section_key(row.section_heading)
        if not name or name in {"アドオン", "性能", "名前"} or not owner:
            continue
        key=(owner,name)
        if key in seen: continue
        seen.add(key)
        rows.append({
            "schema_version": "1.0.0", "record_kind": "ADDON_CANDIDATE",
            "candidate_id": _stable_candidate_id("addon", f"{owner}:{name}"), "canonical_addon_id": None,
            "name_ja": name, "aliases_ja": _aliases(name, name_cell),
            "owner_killer_name_ja": owner, "rarity": _parse_rarity(detail.text),
            "source_effect_ja": _effect(detail.text) or detail.text[:4000],
            "detail_url": detail_url, "image_urls": images,
            "review_status": "CANDIDATE", "source_authority": "COMMUNITY_REFERENCE",
            "source_section_heading": row.section_heading, "source_sections": _row_source_sections(row), "source_page_url": page_url,
        })
    return rows


def parse_map_page(html_text: str, *, page_url: str) -> list[dict[str, object]]:
    parser = _KamigameHTMLParser(base_url=page_url, article_scope=True); parser.feed(html_text)
    if parser.structure_status != "ACCEPTED":
        raise ValueError("Kamigame map page structure is not recognized; Human review is required")
    records: dict[str, dict[str, object]] = {}
    for row in parser.rows:
        if "各マップ個別一覧" not in _clean_text(row.section_heading):
            continue
        if len(row.cells) < 2:
            continue
        first, second = row.cells[0], row.cells[1]
        detail_text = _clean_text(" ".join(cell.text for cell in row.cells[1:]))
        links = [link for link in first.links if link.text]
        if not links:
            continue
        # Map rows contain a map detail link followed by a Realm link/text.
        map_name = _clean_text(links[0].text)
        if not map_name or map_name in {"マップ", "マップ名/エリア名"}:
            continue
        realm_name = _clean_text(links[1].text) if len(links) > 1 else ""
        detail_url = links[0].href if _same_kamigame_page(links[0].href) else None
        text = detail_text
        area_m2 = None
        pallet_text = ""
        m_area = re.search(r"(?:面積|広さ)?\s*([0-9]{4,6})", text)
        if m_area:
            try: area_m2 = int(m_area.group(1))
            except ValueError: pass
        m_pallet = re.search(r"板(?:最大|枚数)?\s*([0-9]+(?:[~〜-][0-9]+)?)", text)
        if m_pallet: pallet_text = m_pallet.group(1)
        size = ""
        for token in ("面積大", "面積中", "面積小"):
            if token in text: size = token[-1]; break
        candidate_id = _stable_candidate_id("map", map_name)
        previous = records.get(candidate_id, {})
        records[candidate_id] = {
            "schema_version": "1.0.0", "record_kind": "MAP_CANDIDATE",
            "candidate_id": candidate_id, "canonical_map_id": None,
            "name_ja": map_name, "aliases_ja": [], "realm_name_ja": realm_name or previous.get("realm_name_ja", ""),
            "detail_url": detail_url or previous.get("detail_url"),
            "image_urls": list(dict.fromkeys([*previous.get("image_urls", []), *first.images, *[img for cell in row.cells[1:] for img in cell.images]])),
            "area_m2": area_m2 if area_m2 is not None else previous.get("area_m2"),
            "pallet_text": pallet_text or previous.get("pallet_text", ""),
            "size_class": size or previous.get("size_class", ""),
            "environment_type": "INDOOR" if "室内" in text else ("OUTDOOR" if "室外" in text else previous.get("environment_type", "")),
            "review_status": "CANDIDATE", "source_authority": "COMMUNITY_REFERENCE",
            "source_section_heading": row.section_heading, "source_sections": _row_source_sections(row), "source_page_url": page_url,
            "source_template_id": parser.template_id, "source_structure_status": parser.structure_status,
        }
    return list(records.values())


def parse_map_detail_page(html_text: str, *, page_url: str) -> dict[str, object]:
    """Extract bounded map-detail metadata without promoting community data to canonical truth."""
    parser = _KamigameHTMLParser(base_url=page_url, article_scope=True); parser.feed(html_text)
    if parser.structure_status != "ACCEPTED":
        return {
            "realm_name_ja": "",
            "offering_name_ja": "",
            "features": "",
            "unique_objects": "",
            "favorability": "",
            "pallet_text": "",
            "area_m2": None,
            "size_class": "",
            "map_image_urls": [],
            "all_image_urls": [],
            "detail_url": page_url,
            "template_id": "UNKNOWN",
            "structure_status": "UNKNOWN_STRUCTURE",
            "requires_human_review": True,
        }
    realm_name = ""; offering_name = ""; pallet_text = ""; area_m2 = None; size_class = ""
    expect_realm_offering = False
    expect_dimensions = False
    for row in parser.rows:
        texts = [cell.text for cell in row.cells]
        if len(row.cells) >= 2:
            if not realm_name and any("領域名" in x for x in texts) and any("オファリング" in x for x in texts):
                expect_realm_offering = True
                continue
            if expect_realm_offering:
                expect_realm_offering = False
                if row.cells[0].links and row.cells[1].links:
                    left = _clean_text(row.cells[0].links[0].text)
                    right = _clean_text(row.cells[1].links[0].text)
                    if left and right:
                        realm_name, offering_name = left, right
                continue
            if area_m2 is None and len(row.cells) >= 3 and "板" in texts[0] and "面積" in texts[1] and "広さ" in texts[2]:
                expect_dimensions = True
                continue
            if expect_dimensions and len(row.cells) >= 3:
                expect_dimensions = False
                p, a, z = texts[0], texts[1], texts[2]
                if "枚" in p and "㎡" in a:
                    pallet_text = p.replace("枚", "").strip()
                    m = re.search(r"([0-9]{4,6})", a)
                    if m:
                        area_m2 = int(m.group(1))
                    size_class = z.strip()
                continue
    text = parser.text
    features = ""
    match = re.search(r"特徴・固有オブジェクト\s*(.*?)\s*有利度", text)
    if match:
        features = _clean_text(match.group(1))[:4000]
    favorability = ""
    match = re.search(r"有利度\s*(.*?)\s*板\s+面積", text)
    if match:
        favorability = _clean_text(match.group(1))[:256]
    # Images directly underneath the map-overview section are preferred over article/header images.
    map_images = [url for heading, url in parser.section_images if "見取り図" in heading]
    return {
        "realm_name_ja": realm_name,
        "offering_name_ja": offering_name,
        "features": features,
        "unique_objects": features,
        "favorability": favorability,
        "pallet_text": pallet_text,
        "area_m2": area_m2,
        "size_class": size_class,
        "map_image_urls": list(dict.fromkeys(map_images))[:8],
        "all_image_urls": list(dict.fromkeys(parser.images))[:128],
        "detail_url": page_url,
        "template_id": parser.template_id,
        "structure_status": parser.structure_status,
        "requires_human_review": False,
    }


def _asset_allowed(url: str) -> bool:
    p = urlparse(url)
    host = (p.hostname or "").casefold()
    return p.scheme == "https" and any(host == suffix or (suffix.startswith(".") and host.endswith(suffix)) for suffix in _ALLOWED_ASSET_HOST_SUFFIXES)


def _image_extension(content_type: str) -> str:
    return {
        "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
        "image/webp": ".webp", "image/bmp": ".bmp",
    }.get(content_type.casefold(), ".img")

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

    def fetch_asset(self, url: str, *, output_stem: Path) -> FetchReceipt:
        if not _asset_allowed(url):
            raise ValueError("collector asset URL is outside the bounded image allow-list")
        delay = self.minimum_delay_seconds - (time.monotonic() - self._last_request_at)
        if delay > 0:
            time.sleep(delay)
        request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "image/*"})
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - allow-listed image hosts
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                raise ValueError(f"unexpected asset content type: {content_type}")
            body = response.read(12 * 1024 * 1024 + 1)
            if len(body) > 12 * 1024 * 1024:
                raise ValueError("asset exceeds 12 MiB safety limit")
        self._last_request_at = time.monotonic()
        output_path = output_stem.with_suffix(_image_extension(content_type))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(body)
        return FetchReceipt(url, output_path, hashlib.sha256(body).hexdigest(), utc_now_iso(), content_type)


def _write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> int:
    rows = list(rows); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as h:
        for row in rows: h.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return len(rows)


def _dedupe(records: Iterable[dict[str, object]], key: str) -> list[dict[str, object]]:
    items = {str(record[key]): record for record in records}; return [items[k] for k in sorted(items)]


class KamigameDbDKnowledgeCollector:
    _PERF_STAGES = (
        "source_index_fetch", "candidate_discovery", "detail_page_fetch", "parse",
        "image_fetch", "normalize", "db_upsert", "alias_index_update", "post_process",
    )

    def __init__(
        self, output_root: str | Path, *, client: KamigameHTTPClient | None = None,
        dedupe_within_run: bool = True,
    ) -> None:
        self.output_root = Path(output_root)
        self.client = client or KamigameHTTPClient()
        self.raw_root = self.output_root / "raw"
        self.normalized_root = self.output_root / "normalized"
        self.dedupe_within_run = bool(dedupe_within_run)
        self._html_fetch_cache: dict[str, FetchReceipt] = {}
        self._asset_fetch_cache: dict[str, FetchReceipt] = {}
        self._perf_seconds: dict[str, float] = {}
        self._perf_counts: dict[str, int] = {}

    def _reset_metrics(self) -> None:
        self._html_fetch_cache.clear()
        self._asset_fetch_cache.clear()
        self._perf_seconds = {stage: 0.0 for stage in self._PERF_STAGES}
        self._perf_counts = {
            "html_requests": 0, "html_cache_hits": 0,
            "asset_requests": 0, "asset_cache_hits": 0,
            "list_pages": 0, "detail_pages": 0, "parsed_records": 0,
        }

    def _add_elapsed(self, stage: str, started: float) -> None:
        self._perf_seconds[stage] = self._perf_seconds.get(stage, 0.0) + max(0.0, time.monotonic() - started)

    @staticmethod
    def _clone_receipt(receipt: FetchReceipt, output_path: Path) -> FetchReceipt:
        return FetchReceipt(receipt.url, output_path, receipt.content_sha256, receipt.retrieved_at, receipt.content_type)

    def _fetch_html(self, url: str, *, output_path: Path, stage: str) -> FetchReceipt:
        started = time.monotonic()
        try:
            cached = self._html_fetch_cache.get(url) if self.dedupe_within_run else None
            if cached is not None and cached.path.is_file():
                self._perf_counts["html_cache_hits"] += 1
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if cached.path.resolve() != output_path.resolve():
                    shutil.copyfile(cached.path, output_path)
                return self._clone_receipt(cached, output_path)
            receipt = self.client.fetch_html(url, output_path=output_path)
            self._perf_counts["html_requests"] += 1
            if self.dedupe_within_run:
                self._html_fetch_cache[url] = receipt
            return receipt
        finally:
            self._add_elapsed(stage, started)

    def _fetch_asset(self, url: str, *, output_stem: Path) -> FetchReceipt:
        started = time.monotonic()
        try:
            cached = self._asset_fetch_cache.get(url) if self.dedupe_within_run else None
            if cached is not None and cached.path.is_file():
                self._perf_counts["asset_cache_hits"] += 1
                output_path = output_stem.with_suffix(cached.path.suffix)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if cached.path.resolve() != output_path.resolve():
                    shutil.copyfile(cached.path, output_path)
                return self._clone_receipt(cached, output_path)
            receipt = self.client.fetch_asset(url, output_stem=output_stem)
            self._perf_counts["asset_requests"] += 1
            if self.dedupe_within_run:
                self._asset_fetch_cache[url] = receipt
            return receipt
        finally:
            self._add_elapsed("image_fetch", started)

    def _crawl_list(self, start_url: str, *, kind: str, max_pages: int) -> tuple[list[dict[str, object]], list[FetchReceipt]]:
        pending=[start_url]; visited:set[str]=set(); receipts:list[FetchReceipt]=[]; records:list[dict[str, object]]=[]
        while pending and len(visited)<max_pages:
            url=pending.pop(0)
            if url in visited: continue
            visited.add(url); raw=self.raw_root/kind/f"page-{len(visited):03d}.html"
            receipt=self._fetch_html(url, output_path=raw, stage="source_index_fetch"); receipts.append(receipt)
            self._perf_counts["list_pages"] += 1
            text=raw.read_text(encoding="utf-8", errors="replace")
            parse_started = time.monotonic(); before = len(records)
            try:
                if kind=="survivor-perks": records.extend(parse_perk_page(text,page_url=url,role="SURVIVOR"))
                elif kind=="killer-perks": records.extend(parse_perk_page(text,page_url=url,role="KILLER"))
                elif kind=="killers": records.extend(parse_killer_list_page(text,page_url=url))
                elif kind=="items": records.extend(parse_item_page(text,page_url=url))
                elif kind=="addons": records.extend(parse_addon_page(text,page_url=url))
                elif kind=="maps": records.extend(parse_map_page(text,page_url=url))
                else: raise ValueError(f"unsupported collector kind: {kind}")
            finally:
                self._add_elapsed("parse", parse_started)
            self._perf_counts["parsed_records"] += len(records) - before
            discovery_started = time.monotonic()
            try:
                next_pages = discover_next_pages(text,page_url=url)
            finally:
                self._add_elapsed("candidate_discovery", discovery_started)
            for nxt in next_pages:
                if nxt not in visited and nxt not in pending: pending.append(nxt)
        return records,receipts

    def collect(self, *, follow_killer_details: bool=True, follow_map_details: bool=True, max_pages: int=20, max_killer_details: int=128, max_map_details: int=128) -> dict[str, object]:
        total_started = time.monotonic()
        self._reset_metrics()
        self.output_root.mkdir(parents=True, exist_ok=True)
        survivor, rs = self._crawl_list(SURVIVOR_PERKS_URL, kind="survivor-perks", max_pages=max_pages)
        killer_perks, rkp = self._crawl_list(KILLER_PERKS_URL, kind="killer-perks", max_pages=max_pages)
        killers, rk = self._crawl_list(KILLERS_URL, kind="killers", max_pages=max_pages)
        items, ri = self._crawl_list(ITEMS_URL, kind="items", max_pages=max_pages)
        addons, ra = self._crawl_list(ADDONS_URL, kind="addons", max_pages=max_pages)
        maps, rm = self._crawl_list(MAPS_URL, kind="maps", max_pages=max_pages)
        map_details: dict[str, dict[str, object]] = {}; rmd: list[FetchReceipt] = []
        if follow_map_details:
            for i, map_row in enumerate(maps[:max_map_details], 1):
                url = map_row.get("detail_url")
                if not isinstance(url, str) or not url:
                    continue
                raw = self.raw_root / "map-details" / f"{i:03d}-{map_row['candidate_id']}.html"
                receipt = self._fetch_html(url, output_path=raw, stage="detail_page_fetch"); rmd.append(receipt)
                self._perf_counts["detail_pages"] += 1
                parse_started = time.monotonic()
                try:
                    map_details[str(map_row["candidate_id"])] = parse_map_detail_page(
                        raw.read_text(encoding="utf-8", errors="replace"), page_url=url
                    )
                finally:
                    self._add_elapsed("parse", parse_started)
        details: dict[str, dict[str, object]] = {}; rd: list[FetchReceipt] = []
        if follow_killer_details:
            for i, killer in enumerate(killers[:max_killer_details], 1):
                url = killer.get("detail_url")
                if not isinstance(url, str) or not url:
                    continue
                raw = self.raw_root / "killer-details" / f"{i:03d}-{killer['candidate_id']}.html"
                receipt = self._fetch_html(url, output_path=raw, stage="detail_page_fetch"); rd.append(receipt)
                self._perf_counts["detail_pages"] += 1
                parse_started = time.monotonic()
                try:
                    details[str(killer["candidate_id"])] = parse_killer_detail_page(
                        raw.read_text(encoding="utf-8", errors="replace"), page_url=url
                    )
                finally:
                    self._add_elapsed("parse", parse_started)
        normalize_started = time.monotonic()
        survivor = _dedupe(survivor, "candidate_id")
        killer_perks = _dedupe(killer_perks, "candidate_id")
        killers = _dedupe(killers, "candidate_id")
        items = _dedupe(items, "candidate_id")
        addons = _dedupe(addons, "candidate_id")
        maps = _dedupe(maps, "candidate_id")
        asset_receipts: list[FetchReceipt] = []
        for map_row in maps:
            detail = map_details.get(str(map_row["candidate_id"]))
            if detail:
                for key in ("realm_name_ja","offering_name_ja","features","unique_objects","favorability","pallet_text","area_m2","size_class"):
                    value = detail.get(key)
                    if value not in (None, ""):
                        map_row[key] = value
                map_row["image_urls"] = list(dict.fromkeys([*detail.get("map_image_urls", []), *map_row.get("image_urls", []), *detail.get("all_image_urls", [])]))
            urls = [str(x) for x in map_row.get("image_urls", []) if str(x)]
            if urls and hasattr(self.client, "fetch_asset"):
                try:
                    asset = self._fetch_asset(urls[0], output_stem=self.output_root / "assets" / "maps" / str(map_row["candidate_id"]))
                    asset_receipts.append(asset)
                    map_row["local_image_path"] = asset.path.relative_to(self.output_root).as_posix()
                except Exception as exc:
                    map_row["image_cache_warning"] = f"{type(exc).__name__}: {exc}"
        # Cache representative item/add-on icons when available; failures remain non-fatal evidence warnings.
        for kind_name, records in (("items", items), ("addons", addons)):
            for row in records:
                urls = [str(x) for x in row.get("image_urls", []) if str(x)]
                if not urls or not hasattr(self.client, "fetch_asset"):
                    continue
                try:
                    asset = self._fetch_asset(urls[0], output_stem=self.output_root / "assets" / kind_name / str(row["candidate_id"]))
                    asset_receipts.append(asset)
                    row["local_image_path"] = asset.path.relative_to(self.output_root).as_posix()
                except Exception as exc:
                    row["image_cache_warning"] = f"{type(exc).__name__}: {exc}"
        for killer in killers:
            if str(killer["candidate_id"]) in details:
                killer["detail"] = details[str(killer["candidate_id"])]
        outputs = {
            "survivor_perks": ("survivor-perks.jsonl", survivor),
            "killer_perks": ("killer-perks.jsonl", killer_perks),
            "killers": ("killers.jsonl", killers),
            "items": ("items.jsonl", items),
            "addons": ("addons.jsonl", addons),
            "maps": ("maps.jsonl", maps),
        }
        for _key, (filename, rows) in outputs.items():
            _write_jsonl(self.normalized_root / filename, rows)
        sources=[]
        for r in [*rs,*rkp,*rk,*ri,*ra,*rm,*rmd,*rd,*asset_receipts]:
            sources.append({"schema_version":"1.0.0","source_id":_source_id(r.url,r.content_sha256),"source_type":"KAMIGAME_ASSET" if r.content_type.startswith("image/") else "KAMIGAME_HTML","authority":"COMMUNITY_REFERENCE","url":r.url,"retrieved_at":r.retrieved_at,"content_sha256":r.content_sha256,"raw_path":r.path.relative_to(self.output_root).as_posix(),"locale":"ja-JP"})
        sources=_dedupe(sources,"source_id"); _write_jsonl(self.normalized_root/"sources.jsonl",sources)
        aliases=self.normalized_root/"aliases.csv"; aliases.parent.mkdir(parents=True,exist_ok=True)
        with aliases.open("w",encoding="utf-8-sig",newline="") as h:
            w=csv.writer(h); w.writerow(["record_kind","candidate_id","canonical_id","locale","alias","review_status"])
            for record in [*survivor,*killer_perks]:
                w.writerow(["PERK",record["candidate_id"],"","ja-JP",record["name_ja"],"CANDIDATE"])
                for alias in record.get("aliases_ja",[]): w.writerow(["PERK",record["candidate_id"],"","ja-JP",alias,"CANDIDATE"])
            for kind, records in (("KILLER", killers),("ITEM",items),("ADDON",addons),("MAP",maps)):
                for record in records:
                    w.writerow([kind,record["candidate_id"],"","ja-JP",record["name_ja"],"CANDIDATE"])
                    for alias in record.get("aliases_ja",[]): w.writerow([kind,record["candidate_id"],"","ja-JP",alias,"CANDIDATE"])
        self._add_elapsed("normalize", normalize_started)
        total_seconds = max(0.0, time.monotonic() - total_started)
        performance = {
            "elapsed_seconds": {
                "total": round(total_seconds, 6),
                **{stage: round(self._perf_seconds.get(stage, 0.0), 6) for stage in self._PERF_STAGES},
            },
            "counts": dict(self._perf_counts),
            "dedupe_within_run": self.dedupe_within_run,
            "note": "db_upsert/alias_index_update are outside the collector and remain zero here; Training Studio measures them separately.",
        }
        body={
            "schema_version":"1.1.0","collector":"KAMIGAME_DBD_KNOWLEDGE","generated_at":utc_now_iso(),
            "authority":"COMMUNITY_REFERENCE","automatic_verification":False,"canonical_write_performed":False,
            "performance":performance,
            "source_urls":[SURVIVOR_PERKS_URL,KILLER_PERKS_URL,KILLERS_URL,ITEMS_URL,ADDONS_URL,MAPS_URL],
            "counts":{
                "survivor_perks":len(survivor),"killer_perks":len(killer_perks),"killers":len(killers),
                "items":len(items),"addons":len(addons),"maps":len(maps),
                "killer_details":len(details),"map_details":len(map_details),"cached_images":len(asset_receipts),"source_snapshots":len(sources),
            },
            "outputs":{
                "survivor_perks":"normalized/survivor-perks.jsonl","killer_perks":"normalized/killer-perks.jsonl",
                "killers":"normalized/killers.jsonl","items":"normalized/items.jsonl","addons":"normalized/addons.jsonl",
                "maps":"normalized/maps.jsonl","aliases":"normalized/aliases.csv","sources":"normalized/sources.jsonl",
            },
        }
        manifest={**body,"manifest_sha256":sha256_bytes(canonical_json_bytes(body))}
        (self.output_root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return manifest
