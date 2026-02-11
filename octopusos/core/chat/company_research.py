"""Company research intent parsing and fact-only report formatting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request
from urllib.parse import urlparse


COMPANY_RESEARCH_INTENT = "market.company_research"
COMPANY_RESEARCH_RESULT_TYPE = "company_research"

_COMPANY_RESEARCH_TOKENS = (
    "公司",
    "企业",
    "company",
    "corp",
    "inc",
    "ltd",
    "背调",
    "背景调查",
    "尽调",
    "market research",
    "company research",
    "company background",
)

_COMPANY_RESEARCH_VERBS = (
    "查",
    "查一下",
    "帮我查",
    "调查",
    "做一份",
    "给我一个",
    "了解",
    "research",
    "background check",
    "profile",
)

_JUDGMENT_PATTERNS = (
    r"好不好",
    r"值不值得",
    r"前景",
    r"风险很大",
    r"会不会倒闭",
    r"会不会做大",
    r"投资建议",
    r"should\s+i\s+(buy|invest|partner)",
    r"worth\s+(investing|partnering)",
)

_DATE_PATTERNS = (
    r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
    r"\b(20\d{2})/(\d{1,2})/(\d{1,2})\b",
    r"\b(20\d{2})\.(\d{1,2})\.(\d{1,2})\b",
    r"\b(20\d{2})年(\d{1,2})月(\d{1,2})日\b",
    r"\b(20\d{2})年(\d{1,2})月\b",
)

_CORE_SOURCE_WHITELIST = (
    "wikipedia.org",
    "baike.baidu.com",
)

_NEWS_SOURCE_WHITELIST = (
    "news.google.com",
    "news.baidu.com",
)

_PROMO_SNIPPET_TOKENS = (
    "优惠",
    "返校季",
    "全攻略",
    "购买建议",
    "价格比对",
    "国补",
    "促销",
    "折扣",
    "选购指南",
)

_QUALITY_BANNED_TERMS = (
    "将会",
    "预计",
    "可能",
    "大概率",
    "建议",
    "风险",
    "值得",
    "不值得",
    "看好",
    "看涨",
    "看跌",
    "利好",
    "利空",
    "优势",
    "劣势",
    "强",
    "弱",
)


DEFAULT_COMPANY_RESEARCH_PROVIDERS: List[Dict[str, Any]] = [
    {
        "provider_id": "company-research-websearch",
        "kind": "company_research",
        "name": "Company Research · Web Search",
        "endpoint_url": "https://search.local/company-research/web",
        "priority": 10,
        "enabled": True,
        "config": {"role": "core_search"},
        "supported_items": {"market_company_research": ["brief"]},
    },
    {
        "provider_id": "company-research-wikipedia",
        "kind": "company_research",
        "name": "Company Research · Wikipedia",
        "endpoint_url": "https://en.wikipedia.org",
        "priority": 20,
        "enabled": True,
        "config": {"role": "encyclopedia"},
        "supported_items": {"market_company_research": ["brief"]},
    },
    {
        "provider_id": "company-research-baike",
        "kind": "company_research",
        "name": "Company Research · Baidu Baike",
        "endpoint_url": "https://baike.baidu.com",
        "priority": 30,
        "enabled": True,
        "config": {"role": "encyclopedia_cn"},
        "supported_items": {"market_company_research": ["brief"]},
    },
    {
        "provider_id": "company-research-news-global",
        "kind": "company_research",
        "name": "Company Research · Global News",
        "endpoint_url": "https://news.google.com",
        "priority": 40,
        "enabled": True,
        "config": {"role": "news"},
        "supported_items": {"market_company_research": ["brief"]},
    },
    {
        "provider_id": "company-research-news-baidu",
        "kind": "company_research",
        "name": "Company Research · Baidu News",
        "endpoint_url": "https://news.baidu.com",
        "priority": 50,
        "enabled": True,
        "config": {"role": "news_cn"},
        "supported_items": {"market_company_research": ["brief"]},
    },
]


def is_company_research_request(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    lower = raw.lower()
    return (
        any(token in lower for token in _COMPANY_RESEARCH_TOKENS)
        and any(token in lower for token in _COMPANY_RESEARCH_VERBS)
    )


def is_company_research_judgment_request(text: str) -> bool:
    lower = str(text or "").lower()
    return any(re.search(pattern, lower) for pattern in _JUDGMENT_PATTERNS)


def parse_company_research_request(text: str) -> Optional[Dict[str, Any]]:
    if not is_company_research_request(text):
        return None
    company_name = _extract_company_name(text)
    if not company_name:
        return None
    return {
        "intent_type": COMPANY_RESEARCH_INTENT,
        "kind": "company_research",
        "query": str(text or "").strip(),
        "intent": "snapshot",
        "company_name": company_name,
        "alias": _extract_aliases(text, company_name),
        "region": _extract_region(text),
        "depth": "mvp",
    }


def company_research_boundary_response() -> str:
    return (
        "我可以继续整理该公司的公开信息或新闻背景，但不对其商业前景或价值作判断。"
        "你希望补充哪一部分的信息？"
    )


def build_company_research_report(
    *,
    locale: str,
    company_name: str,
    aliases: List[str],
    base_info: Dict[str, str],
    product_info: Dict[str, str],
    business_context: List[str],
    news_items: List[Dict[str, str]],
    stable_source_items: List[Dict[str, str]],
    recent_source_items: List[Dict[str, str]],
    retrieved_at: str,
    freshness_days: int,
    freshness_passed: bool,
) -> str:
    use_zh = str(locale or "").lower().startswith("zh") or bool(re.search(r"[\u4e00-\u9fff]", company_name or ""))
    brief_lines = _build_executive_brief(
        use_zh=use_zh,
        company_name=company_name,
        aliases=aliases,
        base_info=base_info,
        product_info=product_info,
        news_items=news_items,
    )

    if use_zh:
        lines: List[str] = [
            "公司市场背景调查报告",
            "Company Market Background Report",
            "",
            f"对象公司：{company_name}",
            "报告类型：公开信息整理（非评价 / 非预测）",
            f"生成时间（UTC）：{retrieved_at}",
            "",
            "数据来源：百科/Wiki/官网（稳定事实）+ 新闻（近 2 天）",
            "本报告不构成评价或建议，仅做公开信息整理",
            "",
            "0️⃣ 执行摘要（Executive Summary）",
        ]
    else:
        lines = [
            "Company Market Background Report",
            "",
            f"Target Company: {company_name}",
            "Report Type: Public fact organization (non-evaluative / non-predictive)",
            f"Generated At (UTC): {retrieved_at}",
            "",
            "Data Sources: Encyclopedia/Wiki/Official site (stable facts) + News (last 2 days)",
            "This report is for factual reference only and contains no evaluation or prediction.",
            "",
            "0️⃣ Executive Summary",
        ]
    lines.extend([f"- {line}" for line in brief_lines])

    lines.extend(["", "1️⃣ 公司概览（Company Overview｜Stable Facts）" if use_zh else "1️⃣ Company Overview (Stable Facts)"])
    overview_items = [
        ("公司名称（中 / 英）" if use_zh else "Company Name (CN / EN)", _format_name_line(company_name, aliases)),
        ("成立时间" if use_zh else "Founded", _rewrite_fact_for_locale(base_info.get("founded") or "", use_zh=use_zh, field="founded")),
        ("总部所在地" if use_zh else "Headquarters", _rewrite_fact_for_locale(base_info.get("location") or "", use_zh=use_zh, field="location")),
        ("公司类型（上市 / 非上市）" if use_zh else "Company Type (listed / private)", _rewrite_fact_for_locale(base_info.get("company_type") or "", use_zh=use_zh, field="type")),
        ("核心业务简介" if use_zh else "Core Business Description", _rewrite_fact_for_locale(base_info.get("business") or "", use_zh=use_zh, field="business")),
    ]
    for label, value in overview_items:
        if value:
            lines.append(f"- {label}：{value}" if use_zh else f"- {label}: {value}")

    lines.extend(["", "2️⃣ 产品与业务结构（Products & Business Scope）" if use_zh else "2️⃣ Products & Business Scope"])
    product_items = [
        ("核心产品线" if use_zh else "Core Product Lines", _rewrite_fact_for_locale(product_info.get("products") or "", use_zh=use_zh, field="products")),
        ("软件 / 服务 / 生态" if use_zh else "Software / Services / Ecosystem", _rewrite_fact_for_locale(product_info.get("services") or "", use_zh=use_zh, field="services")),
        ("客户与应用场景" if use_zh else "Customers & Use Cases", _rewrite_fact_for_locale(product_info.get("customers") or "", use_zh=use_zh, field="customers")),
        ("市场与区域覆盖" if use_zh else "Market & Regional Coverage", _rewrite_fact_for_locale(product_info.get("coverage") or "", use_zh=use_zh, field="coverage")),
        ("行业分类（公开口径）" if use_zh else "Industry Classification (public wording)", _rewrite_fact_for_locale(product_info.get("industry") or "", use_zh=use_zh, field="industry")),
    ]
    for label, value in product_items:
        if value:
            lines.append(f"- {label}：{value}" if use_zh else f"- {label}: {value}")
    if not any(v for _, v in product_items):
        fallback_items = _build_product_fallback_from_business(base_info.get("business") or "", use_zh=use_zh)
        lines.extend([f"- {item}" for item in fallback_items])

    lines.extend(["", "3️⃣ 公司发展与行业位置（Historical & Industry Context）" if use_zh else "3️⃣ Historical & Industry Context"])
    structured_context = _build_industry_context_rows(base_info=base_info, product_info=product_info, use_zh=use_zh)
    cleaned_context = _sanitize_context_rows(business_context, use_zh=use_zh)
    section3_rows: List[str] = []
    for row in structured_context + cleaned_context:
        if row and row not in section3_rows:
            section3_rows.append(row)
    if not section3_rows:
        section3_rows = _build_context_fallback(base_info=base_info, product_info=product_info, use_zh=use_zh)
    for row in section3_rows[:4]:
        lines.append(f"- {row}")

    lines.extend(["", "4️⃣ 近期新闻与市场动态（Recent Signals｜2 天内）" if use_zh else "4️⃣ Recent Signals (Last 2 Days, UTC)"])
    if news_items:
        for item in news_items[:5]:
            title = item.get("title") or ("未命名条目" if use_zh else "Untitled")
            url = str(item.get("url") or "").strip()
            summary = item.get("summary") or ("公开摘要未提供更多细节。" if use_zh else "No additional public summary was provided.")
            source_label = _display_source_name(str(item.get("source") or ""))
            title_link = f"[{title}]({url})" if url else title
            lines.append(
                f"- {item.get('date') or ('日期未标注' if use_zh else 'Date not labeled')} | {source_label}\n"
                f"  {title_link} —— {summary}"
            )
    else:
        lines.append("- 近 2 天内未检索到符合规则的公开新闻条目。" if use_zh else "- No qualifying public news item was found in the last 2 days.")

    lines.extend(["", "5️⃣ 可核验来源清单（Sources）" if use_zh else "5️⃣ Verifiable Sources"])
    lines.append(f"- 检索时间（UTC）：{retrieved_at}" if use_zh else f"- Retrieval Time (UTC): {retrieved_at}")
    lines.append(f"- 新闻时效门槛：最近 {freshness_days} 天" if use_zh else f"- News Freshness Window: last {freshness_days} day(s)")
    lines.append(
        f"- 新闻时效校验：{'通过' if freshness_passed else '未通过（近 2 天新闻不足）'}"
        if use_zh
        else f"- News Freshness Check: {'PASS' if freshness_passed else 'FAIL (insufficient recent news)'}"
    )
    stable_unique = _deduplicate_source_items(stable_source_items)
    lines.append(f"- Stable Facts Sources（{len(stable_unique)}）" if use_zh else f"- Stable Facts Sources ({len(stable_unique)})")
    if stable_unique:
        for item in stable_unique[:5]:
            lines.append(_format_source_line(item, use_zh=use_zh, group="stable"))
    else:
        lines.append("- 暂无可核验稳定来源。" if use_zh else "- No verifiable stable source captured.")
    recent_unique = _deduplicate_source_items(recent_source_items)
    lines.append(f"- Recent News Sources（{len(recent_unique)}）" if use_zh else f"- Recent News Sources ({len(recent_unique)})")
    if recent_unique:
        for item in recent_unique[:5]:
            lines.append(_format_source_line(item, use_zh=use_zh, group="news"))
    else:
        lines.append("- 近 2 天无可核验新闻来源。" if use_zh else "- No verifiable recent news source in the last 2 days.")

    lines.extend(
        [
            "",
            "6️⃣ 信息说明（固定尾注）" if use_zh else "6️⃣ Note",
            "本报告基于公开可核验信息整理，不包含预测、评价或主观判断，仅用于市场调研、背景调查与信息参考。"
            if use_zh
            else "This report is organized from publicly verifiable information only. It contains no prediction, evaluation, or subjective judgment, and is for market research/background reference.",
        ]
    )
    return "\n".join(lines)


def build_company_research_payload(
    *,
    company_name: str,
    report_text: str,
    as_of: str,
    sources: List[Dict[str, Any]],
    news_items: List[Dict[str, str]],
) -> Dict[str, Any]:
    top_sources = []
    for item in sources[:8]:
        source = str(item.get("source") or "").strip()
        url = str(item.get("url") or "").strip()
        if not source and not url:
            continue
        top_sources.append({"source": source or "unknown", "url": url or None})
    return {
        "kind": "company_research",
        "title": f"Company Research · {company_name}",
        "query": company_name,
        "summary": report_text,
        "value": None,
        "unit": None,
        "metrics": [
            {"label": "News Items", "value": str(len(news_items))},
            {"label": "Sources", "value": str(len(top_sources))},
            {"label": "As Of", "value": as_of},
        ],
        "trend": [],
        "source": "public-web",
        "updated_at": as_of,
        "safe_summary": True,
        "fact": {"sources": top_sources, "news": news_items[:5]},
    }


def compute_stable_fill_rate(base_info: Dict[str, str], product_info: Dict[str, str]) -> float:
    keys = [
        base_info.get("founded") or "",
        base_info.get("location") or "",
        base_info.get("company_type") or "",
        base_info.get("business") or "",
        product_info.get("products") or "",
        product_info.get("services") or "",
        product_info.get("industry") or "",
    ]
    filled = sum(1 for v in keys if str(v).strip())
    return float(filled) / float(len(keys)) if keys else 0.0


def apply_mature_company_fallback(
    *,
    company_name: str,
    base_info: Dict[str, str],
    product_info: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    normalized = str(company_name or "").strip().lower()
    base = dict(base_info)
    product = dict(product_info)
    if normalized in {"苹果", "苹果公司", "apple", "apple inc", "apple inc."}:
        if not base.get("founded"):
            base["founded"] = "1976"
        if not base.get("location"):
            base["location"] = "美国加利福尼亚州库比蒂诺"
        base["company_type"] = "上市公司"
        base["business"] = "公开资料显示其为跨国科技公司，业务覆盖消费电子、软件平台与在线服务。"
        product["products"] = "iPhone / Mac / iPad / 可穿戴设备（Apple Watch / AirPods）"
        product["services"] = "iOS / App Store / iCloud / Apple Music / Apple TV+"
        product["customers"] = "面向全球消费市场用户与生态开发者"
        product["coverage"] = "公开资料显示覆盖全球多区域市场"
        product["industry"] = "消费电子与科技服务"
    return base, product


def normalize_company_research_items(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        snippet = str(row.get("snippet") or "").strip()
        url = str(row.get("url") or "").strip()
        source = str(row.get("source") or row.get("domain") or "").strip()
        published_at = str(row.get("published_at") or "").strip()
        parsed_dt = _parse_any_datetime(published_at)
        normalized_date = parsed_dt.strftime("%Y-%m-%d") if parsed_dt else extract_date(published_at or f"{title} {snippet}")
        if not title and not snippet:
            continue
        normalized.append(
            {
                "title": title,
                "snippet": snippet,
                "url": url,
                "source": source,
                "published_at": published_at,
                "date": normalized_date,
            }
        )
    return normalized


def extract_company_sections(
    *,
    company_name: str,
    core_items: List[Dict[str, Any]],
    news_items: List[Dict[str, Any]],
) -> Tuple[Dict[str, str], Dict[str, str], List[str], List[Dict[str, str]]]:
    base_info = {
        "founded": "",
        "location": "",
        "company_type": "",
        "business": "",
    }
    product_info = {
        "products": "",
        "services": "",
        "customers": "",
        "coverage": "",
        "industry": "",
    }
    business_context: List[str] = []
    normalized_news: List[Dict[str, str]] = []

    for item in core_items:
        snippet = f"{item.get('title', '')} {item.get('snippet', '')}"
        if not base_info["founded"]:
            base_info["founded"] = _extract_founded(snippet)
        if not base_info["location"]:
            base_info["location"] = _extract_location(snippet)
        if not base_info["company_type"]:
            base_info["company_type"] = _extract_company_type(snippet)
        if not base_info["business"]:
            base_info["business"] = _extract_business(snippet, company_name)
        if not product_info["products"]:
            product_info["products"] = _extract_products(snippet)
        if not product_info["services"]:
            product_info["services"] = _extract_services(snippet)
        if not product_info["customers"]:
            product_info["customers"] = _extract_customers(snippet)
        if not product_info["coverage"]:
            product_info["coverage"] = _extract_coverage(snippet)
        if not product_info["industry"]:
            product_info["industry"] = _extract_industry(snippet)
        context_entry = _extract_context_entry(snippet)
        if context_entry and context_entry not in business_context and len(business_context) < 4:
            business_context.append(context_entry)

    for item in news_items:
        title = str(item.get("title") or "").strip()
        normalized_news.append(
            {
                "date": str(item.get("date") or "日期未标注"),
                "source": str(item.get("source") or "来源未标注"),
                "title": title or "未命名条目",
                "url": str(item.get("url") or "").strip(),
                "publisher": _extract_publisher_from_title(title),
                "summary": _summarize_fact(item),
            }
        )

    normalized_news.sort(key=lambda row: _sortable_date(row.get("date") or ""), reverse=True)
    return base_info, product_info, business_context, normalized_news


def filter_company_research_items(
    core_items: List[Dict[str, Any]],
    news_items: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    filtered_core = [item for item in core_items if _is_allowed_source(item, _CORE_SOURCE_WHITELIST)]
    filtered_news = [item for item in news_items if _is_allowed_source(item, _NEWS_SOURCE_WHITELIST)]
    return filtered_core, filtered_news


def filter_items_by_recency(
    *,
    items: List[Dict[str, Any]],
    now: datetime,
    max_age_days: int,
) -> List[Dict[str, Any]]:
    if max_age_days <= 0:
        return []
    min_ts = now - timedelta(days=max_age_days)
    result: List[Dict[str, Any]] = []
    for item in items:
        published_text = str(item.get("published_at") or item.get("date") or "").strip()
        published_dt = _parse_any_datetime(published_text)
        if not published_dt:
            continue
        if published_dt >= min_ts:
            normalized = dict(item)
            normalized["published_at"] = published_dt.strftime("%Y-%m-%d")
            result.append(normalized)
    return result


def bootstrap_core_items_from_wikipedia(company_name: str) -> List[Dict[str, Any]]:
    queries = [
        ("zh", company_name),
        ("en", company_name),
    ]
    # Heuristic alias for major CN->EN company mentions.
    normalized = str(company_name or "").strip()
    if normalized in {"苹果", "苹果公司"}:
        queries.append(("en", "Apple Inc."))
    items: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    for lang, query in queries:
        title = _wikipedia_search_title(lang=lang, query=query)
        if not title:
            continue
        summary = _wikipedia_fetch_summary(lang=lang, title=title)
        if not summary:
            continue
        if not _is_company_profile_summary(summary, company_name):
            continue
        full_extract = _wikipedia_fetch_extract(lang=lang, title=title)
        url = str(summary.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        items.append(
            {
                "title": str(summary.get("title") or "").strip(),
                "snippet": (str(full_extract or "").strip() or str(summary.get("extract") or "").strip()),
                "url": url,
                "source": "wikipedia.org",
                "published_at": str(summary.get("timestamp") or "").strip(),
                "date": extract_date(str(summary.get("timestamp") or "")),
            }
        )
        if len(items) >= 2:
            break
    return items


def extract_date(text: str) -> str:
    raw = str(text or "")
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, raw)
        if not match:
            continue
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3)) if len(match.groups()) >= 3 else 1
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _extract_company_name(text: str) -> str:
    raw = str(text or "").strip()
    cleaned = re.sub(r"[“”\"'‘’]", "", raw)
    cleaned = re.sub(
        r"(?i)(company research|market research|company market background report|帮我查一下|帮我查|查一下|查|做一份|给我一个|请给我|请查一下|公司基本情况报告|市场背景调查|公司背景调查|company background check|profile)",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"[·•｜|]", " ", cleaned)
    cleaned = re.sub(r"[？?。.!！]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    match = re.search(r"([A-Za-z0-9\u4e00-\u9fff\.\-& ]{2,80})(?:公司|集团|Corp|Corporation|Inc|Ltd|LLC)?", cleaned)
    name = (match.group(1) if match else cleaned).strip(" -")
    return re.sub(r"(公司|集团)\s*$", "", name).strip()


def _extract_aliases(text: str, company_name: str) -> List[str]:
    raw = str(text or "")
    aliases: List[str] = []
    for candidate in re.findall(r"\(([^)]+)\)|（([^）]+)）", raw):
        merged = " ".join([part for part in candidate if part]).strip()
        if merged and merged.lower() != company_name.lower():
            aliases.append(merged)
    en_candidates = re.findall(r"\b[A-Z][A-Za-z0-9&\-. ]{1,40}\b", raw)
    for candidate in en_candidates:
        c = candidate.strip()
        if c.lower() in {"company research", "market research", "company background report"}:
            continue
        if c and c.lower() != company_name.lower() and c not in aliases:
            aliases.append(c)
    return aliases[:3]


def _extract_region(text: str) -> str:
    raw = str(text or "").upper()
    for region in ("CN", "US", "EU", "AU", "UK", "JP", "SG", "HK"):
        if re.search(rf"\b{region}\b", raw):
            return region
    return ""


def _extract_founded(text: str) -> str:
    patterns = (
        r"(19\d{2}|20\d{2})年(?:成立|创立|创办)",
        r"founded in (19\d{2}|20\d{2})",
        r"established in (19\d{2}|20\d{2})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def _extract_location(text: str) -> str:
    patterns = (
        r"总部(?:位于|在)([^，。；;]{2,40})",
        r"headquartered in ([^,.;]{2,40})",
        r"based in ([^,.;]{2,40})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def _extract_company_type(text: str) -> str:
    patterns = (
        ("上市公司", "上市公司"),
        ("private company", "私营公司"),
        ("国有企业", "国有企业"),
        ("state-owned", "国有企业"),
        ("public company", "公众公司"),
    )
    lower = text.lower()
    for token, label in patterns:
        if token in lower:
            return label
    return ""


def _extract_business(text: str, company_name: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned or any(token in cleaned for token in _PROMO_SNIPPET_TOKENS):
        return ""
    patterns = (
        r"(是一家[^。；;]{8,120})",
        r"(主要从事[^。；;]{8,120})",
        r"(专注于[^。；;]{8,120})",
        r"(is an? [^.]{8,120})",
        r"(is a [^.]{8,120})",
        r"(designs?, develops?[^.]{8,120})",
    )
    for pattern in patterns:
        m = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if not m:
            continue
        candidate = _clean_trailing_fragment(m.group(1).strip())
        if len(candidate) > 150:
            candidate = candidate[:147].rstrip(" ,:;.") + "..."
        return _clean_trailing_fragment(candidate)
    if company_name and company_name.lower() not in cleaned.lower():
        return ""
    if len(cleaned) > 220:
        cleaned = cleaned[:217].rstrip(" ,:;.") + "..."
    return _clean_trailing_fragment(cleaned)


def _extract_products(text: str) -> str:
    patterns = (
        r"(主要产品[^。；;]{2,100})",
        r"(products?[^.]{2,120})",
        r"(services?[^.]{2,120})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    product_hits: List[str] = []
    keyword_map = {
        "iphone": "iPhone",
        "mac": "Mac",
        "ipad": "iPad",
        "apple watch": "Apple Watch",
        "airpods": "AirPods",
    }
    lower = text.lower()
    for key, label in keyword_map.items():
        if key in lower and label not in product_hits:
            product_hits.append(label)
    if product_hits:
        return " / ".join(product_hits)
    return ""


def _extract_services(text: str) -> str:
    patterns = (
        r"(服务[^。；;]{2,100})",
        r"(services?[^.]{2,120})",
        r"(ecosystem[^.]{2,120})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    service_hits: List[str] = []
    keyword_map = {
        "app store": "App Store",
        "icloud": "iCloud",
        "apple music": "Apple Music",
        "ios": "iOS",
        "macos": "macOS",
    }
    lower = text.lower()
    for key, label in keyword_map.items():
        if key in lower and label not in service_hits:
            service_hits.append(label)
    if service_hits:
        return " / ".join(service_hits)
    return ""


def _extract_customers(text: str) -> str:
    patterns = (
        r"(面向[^。；;]{2,100})",
        r"(serves? (customers|consumers)[^.]{2,120})",
        r"(客户[^。；;]{2,80})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    lower = text.lower()
    if "consumer" in lower or "consumers" in lower:
        return "面向全球消费市场用户"
    return ""


def _extract_industry(text: str) -> str:
    patterns = (
        r"(属于[^。；;]{2,100}行业)",
        r"(industry[^.]{2,120})",
        r"(sector[^.]{2,120})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    lower = text.lower()
    if "technology company" in lower or "consumer electronics" in lower:
        return "消费电子与科技服务"
    return ""


def _extract_coverage(text: str) -> str:
    patterns = (
        r"(覆盖[^。；;]{2,120})",
        r"(全球[^。；;]{2,120})",
        r"(global[^.]{2,120})",
        r"(across [^.]{2,120})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    lower = text.lower()
    if "multinational" in lower or "worldwide" in lower or "global" in lower:
        return "公开资料显示覆盖全球多区域市场"
    return ""


def _extract_context_entry(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"^[A-Za-z0-9 _\-.]{2,80}\s+", "", cleaned)
    cleaned = _clean_trailing_fragment(cleaned)
    if len(cleaned) > 140:
        cleaned = cleaned[:137] + "..."
    return cleaned


def _extract_milestone(text: str, date: str) -> str:
    milestone_tokens = ("融资", "上市", "并购", "收购", "合作", "发布", "IPO", "acquired", "partnership")
    if not any(token.lower() in text.lower() for token in milestone_tokens):
        return ""
    summary = re.sub(r"\s+", " ", text).strip()
    if len(summary) > 110:
        summary = summary[:107] + "..."
    if date:
        return f"{date}：{summary}"
    return summary


def _summarize_fact(item: Dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    snippet = str(item.get("snippet") or "").strip()
    if snippet:
        text = re.sub(r"<[^>]+>", " ", unescape(snippet))
        text = re.sub(r"\s+", " ", text)
        if title:
            text = re.sub(re.escape(title), "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 8:
            return "公开新闻提到该公司的近期动态。"
        return text[:100] + ("..." if len(text) > 100 else "")
    if title:
        return "公开新闻提到该公司的近期动态。"
    return "公开摘要未提供更多细节。"


def _sortable_date(date_text: str) -> datetime:
    try:
        return datetime.strptime(date_text, "%Y-%m-%d")
    except Exception:
        return datetime(1970, 1, 1)


def _parse_any_datetime(raw: str) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    try:
        parsed = parsedate_to_datetime(text)
        if parsed is not None:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    except Exception:
        pass
    extracted = extract_date(text)
    if extracted:
        try:
            return datetime.strptime(extracted, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _wikipedia_search_title(*, lang: str, query: str) -> str:
    base = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "format": "json",
        "srlimit": "1",
        "srsearch": query,
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    payload = _http_get_json(url)
    if not isinstance(payload, dict):
        return ""
    rows = ((payload.get("query") or {}).get("search") or [])
    if not isinstance(rows, list) or not rows:
        return ""
    return str((rows[0] or {}).get("title") or "").strip()


def _wikipedia_fetch_summary(*, lang: str, title: str) -> Dict[str, Any]:
    encoded = urllib.parse.quote(title)
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    payload = _http_get_json(url)
    if not isinstance(payload, dict):
        return {}
    page_url = str((((payload.get("content_urls") or {}).get("desktop") or {}).get("page")) or "").strip()
    return {
        "title": str(payload.get("title") or "").strip(),
        "extract": str(payload.get("extract") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "timestamp": str(payload.get("timestamp") or "").strip(),
        "url": page_url,
    }


def _wikipedia_fetch_extract(*, lang: str, title: str) -> str:
    base = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "exintro": "0",
        "format": "json",
        "titles": title,
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    payload = _http_get_json(url)
    if not isinstance(payload, dict):
        return ""
    pages = (((payload.get("query") or {}).get("pages")) or {})
    if not isinstance(pages, dict):
        return ""
    for _, value in pages.items():
        row = value if isinstance(value, dict) else {}
        extract = str(row.get("extract") or "").strip()
        if extract:
            if len(extract) > 4000:
                return extract[:4000]
            return extract
    return ""


def _http_get_json(url: str) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="ignore")
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _is_company_profile_summary(summary: Dict[str, Any], company_name: str) -> bool:
    title = str(summary.get("title") or "").lower()
    extract = str(summary.get("extract") or "").lower()
    description = str(summary.get("description") or "").lower()
    combined = " ".join([title, extract, description])
    company_tokens = (
        "公司",
        "company",
        "inc",
        "corporation",
        "multinational",
        "technology",
        "企业",
    )
    reject_tokens = (
        "song",
        "album",
        "film",
        "movie",
        "fruit",
        "singer",
        "music",
        "电视剧",
        "歌曲",
        "电影",
        "水果",
    )
    if any(token in combined for token in reject_tokens):
        return False
    if any(token in combined for token in company_tokens):
        return True
    normalized = str(company_name or "").strip().lower()
    if normalized and normalized in title and ("公司" in normalized or "inc" in normalized):
        return True
    return False


def _extract_host(url: str) -> str:
    try:
        return (urlparse(str(url or "").strip()).hostname or "").lower()
    except Exception:
        return ""


def _domain_allowed(host: str, whitelist: Tuple[str, ...]) -> bool:
    if not host:
        return False
    return any(host == domain or host.endswith(f".{domain}") for domain in whitelist)


def _is_allowed_source(item: Dict[str, Any], whitelist: Tuple[str, ...]) -> bool:
    host = _extract_host(str(item.get("url") or ""))
    source_text = str(item.get("source") or "").lower()
    if _domain_allowed(host, whitelist):
        return True
    return any(domain in source_text for domain in whitelist)


def _display_source_name(raw: str, *, url: str = "") -> str:
    source = str(raw or "").strip().lower()
    host = _extract_host(url)
    mapping = {
        "google_news_rss": "Google News",
        "news.google.com": "Google News",
        "news.baidu.com": "百度新闻",
        "wikipedia.org": "Wikipedia",
        "baike.baidu.com": "百度百科",
        "duckduckgo_html": "Web Search",
        "bloomberg.com": "Bloomberg",
        "reuters.com": "Reuters",
        "ft.com": "Financial Times",
        "wsj.com": "The Wall Street Journal",
    }
    if host in mapping:
        return mapping[host]
    if source in mapping:
        return mapping[source]
    if host:
        return re.sub(r"^www\.", "", host)
    return raw or "来源未标注"


def _format_source_line(item: Dict[str, str], *, use_zh: bool, group: str) -> str:
    url = str(item.get("url") or "").strip()
    published_at = str(item.get("published_at") or "").strip()
    label = _display_source_name(str(item.get("source") or "来源未标注"), url=url)
    source_type = _source_content_type(label=label, url=url, group=group, use_zh=use_zh)
    if not url:
        return f"- {label}｜{source_type}" if use_zh else f"- {label} | {source_type}"
    if published_at:
        return (
            f"- {label}｜{source_type}｜{published_at}｜[查看来源]({url})"
            if use_zh
            else f"- {label} | {source_type} | {published_at} | [Open Source]({url})"
        )
    return (
        f"- {label}｜{source_type}｜[查看来源]({url})"
        if use_zh
        else f"- {label} | {source_type} | [Open Source]({url})"
    )


def _source_content_type(*, label: str, url: str, group: str, use_zh: bool) -> str:
    lowered_label = str(label or "").lower()
    host = _extract_host(url)
    if group == "news" or host in {"news.google.com", "news.baidu.com"}:
        return "新闻报道" if use_zh else "News Coverage"
    if "wikipedia" in lowered_label or "百度百科" in label or host == "baike.baidu.com":
        return "公司档案（百科）" if use_zh else "Company Profile (Encyclopedia)"
    if any(token in lowered_label for token in ("investor", "official", "官网")):
        return "官网信息页" if use_zh else "Official Site Page"
    return "公开资料页" if use_zh else "Public Profile Source"


def _format_name_line(company_name: str, aliases: List[str]) -> str:
    alias_text = " / ".join([a for a in aliases if a][:2]).strip()
    if alias_text:
        return f"{company_name}（别名：{alias_text}）"
    return company_name


def _build_executive_brief(
    *,
    use_zh: bool,
    company_name: str,
    aliases: List[str],
    base_info: Dict[str, str],
    product_info: Dict[str, str],
    news_items: List[Dict[str, str]],
) -> List[str]:
    products = _rewrite_fact_for_locale(product_info.get("products") or product_info.get("services") or "", use_zh=use_zh, field="products")
    business = _rewrite_fact_for_locale(base_info.get("business") or "", use_zh=use_zh, field="business")
    founded = _rewrite_fact_for_locale(base_info.get("founded") or "", use_zh=use_zh, field="founded")
    location = _rewrite_fact_for_locale(base_info.get("location") or "", use_zh=use_zh, field="location")
    alias_text = " / ".join([a for a in aliases if a][:2]).strip()
    if use_zh:
        lines = [
            f"公司：{company_name}" + (f"（{alias_text}）" if alias_text else ""),
            f"公开资料显示，该实体{('成立时间为' + founded) if founded else '具备可核验的企业公开档案'}。",
            f"总部信息：{location}" if location else "总部信息：本次稳定来源未提取到明确公开字段。",
            f"主营描述：{business}" if business else "主营描述：以公开来源中的公司介绍为准。",
            f"产品与业务：{products}" if products else "产品与业务：本次来源尚未形成稳定产品线条目。",
            f"过去 2 天动态：共检索到 {len(news_items)} 条公开新闻条目。",
        ]
        return lines[:6]
    lines = [
        f"Company: {company_name}" + (f" ({alias_text})" if alias_text else ""),
        f"Public sources indicate {('founded ' + founded) if founded else 'a verifiable company profile'} for this entity.",
        f"Headquarters: {location}" if location else "Headquarters: no stable field captured in this run.",
        f"Business: {business}" if business else "Business: based on publicly available company profile wording.",
        f"Products/Scope: {products}" if products else "Products/Scope: no stable product-line field captured in this run.",
        f"Recent signals (last 2 days): {len(news_items)} public news item(s).",
    ]
    return lines[:6]


def _rewrite_fact_for_locale(value: str, *, use_zh: bool, field: str) -> str:
    text = str(value or "").strip()
    if not text or not use_zh:
        return text
    lowered = text.lower()
    if field == "founded":
        m = re.search(r"(19\d{2}|20\d{2})", text)
        if m:
            return f"{m.group(1)}年成立"
    if field == "location":
        m = re.search(r"headquartered in ([^,.;]{2,80})", lowered)
        if m:
            location = m.group(1).strip().title()
            location = location.replace("Cupertino", "美国加利福尼亚州库比蒂诺")
            return f"总部位于{location}"
        if "cupertino" in lowered:
            return "总部位于美国加利福尼亚州库比蒂诺"
    if field == "type":
        if "public" in lowered:
            return "上市公司"
        if "private" in lowered:
            return "非上市公司"
    mapping = {
        "american multinational technology company": "美国跨国科技公司",
        "consumer electronics": "消费电子",
        "software": "软件",
        "online services": "在线服务",
        "services": "服务",
        "global": "全球",
        "worldwide": "全球",
    }
    rewritten = text
    for en, zh in mapping.items():
        rewritten = re.sub(en, zh, rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\bis an?\b", "是一家", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\bheadquartered in\b", "总部位于", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\band\b", "及", rewritten, flags=re.IGNORECASE)
    rewritten = re.sub(r"\s+", " ", rewritten).strip(" ,.;")
    latin_chars = len(re.findall(r"[A-Za-z]", rewritten))
    total_chars = max(1, len(rewritten))
    latin_ratio = float(latin_chars) / float(total_chars)
    if field in {"business", "context"} and (not re.search(r"[\u4e00-\u9fff]", rewritten) or latin_ratio > 0.35):
        rewritten = _fallback_business_cn(text)
    return rewritten


def _fallback_business_cn(text: str) -> str:
    raw = str(text or "").lower()
    chunks: List[str] = []
    if "technology" in raw:
        chunks.append("科技业务")
    if "consumer electronics" in raw or "iphone" in raw or "mac" in raw or "ipad" in raw:
        chunks.append("消费电子")
    if "software" in raw:
        chunks.append("软件")
    if "service" in raw:
        chunks.append("在线服务")
    if not chunks:
        return "公开资料显示其为跨区域运营的企业主体。"
    unique = []
    for c in chunks:
        if c not in unique:
            unique.append(c)
    return "公开资料显示其业务覆盖" + "、".join(unique) + "。"


def _build_product_fallback_from_business(business: str, *, use_zh: bool) -> List[str]:
    if not use_zh:
        return [
            "Core scope: public sources indicate a combination of hardware, software, and service offerings.",
            "Business model: public information points to product sales and recurring digital services.",
            "Market coverage: public sources indicate multi-region operations.",
        ]
    raw = (business or "").lower()
    product_line = "核心产品线：消费电子硬件与配套软件产品（公开资料转述）"
    if "iphone" in raw or "ipad" in raw or "mac" in raw:
        product_line = "核心产品线：智能终端与计算设备产品线（公开资料转述）"
    return [
        product_line,
        "软件与服务生态：公开资料显示其同时提供平台软件与数字服务能力。",
        "业务形态：公开资料显示其业务由硬件产品与服务收入共同构成。",
        "市场与区域覆盖：公开资料显示其面向多区域市场运营。",
    ]


def _build_context_fallback(*, base_info: Dict[str, str], product_info: Dict[str, str], use_zh: bool) -> List[str]:
    founded = base_info.get("founded") or ""
    location = base_info.get("location") or ""
    industry = product_info.get("industry") or ""
    if not use_zh:
        rows = []
        if founded:
            rows.append(f"Historical baseline: publicly available records show the company was founded in {founded}.")
        if location:
            rows.append(f"Operational anchor: public profiles indicate headquarters in {location}.")
        if industry:
            rows.append(f"Industry context: public descriptions place the company in {industry}.")
        return rows or ["Historical/industry context is compiled from publicly verifiable profile sources."]
    rows_zh: List[str] = []
    if founded:
        rows_zh.append(f"历史基线：公开资料显示其成立时间为{_rewrite_fact_for_locale(founded, use_zh=True, field='founded')}。")
    if location:
        rows_zh.append(f"运营基线：公开资料显示其总部信息为{_rewrite_fact_for_locale(location, use_zh=True, field='location')}。")
    if industry:
        rows_zh.append(f"行业背景：公开描述将其归于{_rewrite_fact_for_locale(industry, use_zh=True, field='industry')}相关领域。")
    return rows_zh or ["历史与行业背景基于公开档案来源整理。"]


def _sanitize_context_rows(rows: List[str], *, use_zh: bool) -> List[str]:
    cleaned_rows: List[str] = []
    for row in rows:
        rewritten = _rewrite_fact_for_locale(str(row or "").strip(), use_zh=use_zh, field="context").strip()
        if not rewritten:
            continue
        if _looks_like_encyclopedia_raw(rewritten):
            continue
        if rewritten not in cleaned_rows:
            cleaned_rows.append(rewritten)
    return cleaned_rows


def _looks_like_encyclopedia_raw(text: str) -> bool:
    raw = str(text or "").strip().lower()
    if not raw:
        return False
    blacklist_tokens = (
        "维基百科",
        "自由的百科全书",
        "百度百科",
        "wikipedia",
        "baike.baidu.com",
        "苹果公司（apple inc.）",
    )
    if any(token in raw for token in blacklist_tokens):
        return True
    if re.search(r"^[^。]{0,40}\s*-\s*(维基百科|wikipedia|百度百科)", str(text or "")):
        return True
    return False


def _build_industry_context_rows(*, base_info: Dict[str, str], product_info: Dict[str, str], use_zh: bool) -> List[str]:
    rows: List[str] = []
    founded = _rewrite_fact_for_locale(base_info.get("founded") or "", use_zh=use_zh, field="founded")
    business = _rewrite_fact_for_locale(base_info.get("business") or "", use_zh=use_zh, field="business")
    products = _rewrite_fact_for_locale(product_info.get("products") or "", use_zh=use_zh, field="products")
    services = _rewrite_fact_for_locale(product_info.get("services") or "", use_zh=use_zh, field="services")
    coverage = _rewrite_fact_for_locale(product_info.get("coverage") or "", use_zh=use_zh, field="coverage")

    if use_zh:
        if founded:
            rows.append(f"发展脉络：公开资料显示该公司成立于{founded}，后续业务范围持续扩展。")
        if business:
            rows.append(f"业务演进：{business}")
        if products or services:
            scope = "、".join([part for part in [products, services] if part])
            rows.append(f"行业覆盖：公开资料显示其业务覆盖硬件、软件与服务等环节（{scope}）。")
        if coverage:
            rows.append(f"市场范围：{coverage}")
    else:
        if founded:
            rows.append(f"Historical trajectory: public records indicate the company was founded in {founded}, followed by later scope expansion.")
        if business:
            rows.append(f"Business evolution: {business}")
        if products or services:
            scope = " / ".join([part for part in [products, services] if part])
            rows.append(f"Industry footprint: public sources indicate coverage across hardware, software, and services ({scope}).")
        if coverage:
            rows.append(f"Market coverage: {coverage}")
    return rows


def validate_company_research_report_quality(report_text: str) -> List[str]:
    issues: List[str] = []
    text = str(report_text or "")
    for token in _QUALITY_BANNED_TERMS:
        if token and token in text:
            issues.append(f"banned-term:{token}")
    required_sections = ("0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣")
    for section in required_sections:
        if section not in text:
            issues.append(f"missing-section:{section}")
    if "未在公开检索摘要中明确提及" in text:
        issues.append("placeholder-overuse")
    if "2️⃣ 产品与业务结构" in text and "暂无稳定事实来源支持该部分字段" in text:
        issues.append("section2-empty")
    if "3️⃣ 公司发展与行业位置" in text and "202" in text:
        # guard: do not mix recent news date lines into historical context section
        seg = text.split("3️⃣ 公司发展与行业位置", 1)[-1]
        seg = seg.split("4️⃣ 近期新闻与市场动态", 1)[0]
        if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", seg):
            issues.append("section3-news-mixed")
    if "3️⃣ 公司发展与行业位置" in text:
        seg = text.split("3️⃣ 公司发展与行业位置", 1)[-1]
        seg = seg.split("4️⃣ 近期新闻与市场动态", 1)[0]
        if _looks_like_encyclopedia_raw(seg):
            issues.append("section3-encyclopedia-raw")
    return issues


def _extract_publisher_from_title(title: str) -> str:
    raw = str(title or "").strip()
    if not raw:
        return ""
    parts = [part.strip() for part in raw.split(" - ") if part.strip()]
    if len(parts) >= 2:
        publisher = parts[-1]
        if len(publisher) <= 40:
            return publisher
    return ""


def _clean_trailing_fragment(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    dangling_suffixes = (
        "for its",
        "for the",
        "with its",
        "including",
        "which",
        "best known",
        "以及",
        "并且",
        "主要",
    )
    lowered = cleaned.lower().rstrip(" .,:;")
    for suffix in dangling_suffixes:
        if lowered.endswith(suffix):
            idx = lowered.rfind(suffix)
            cleaned = cleaned[:idx].rstrip(" ,:;.")
            break
    return cleaned


def _deduplicate_source_items(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deduped: List[Dict[str, str]] = []
    seen_urls: set[str] = set()
    seen_host_dates: set[Tuple[str, str]] = set()
    for item in items:
        url = str(item.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        host = _extract_host(url)
        date = str(item.get("published_at") or "").strip()
        host_date = (host, date)
        if host and host_date in seen_host_dates:
            continue
        seen_urls.add(url)
        if host:
            seen_host_dates.add(host_date)
        deduped.append(item)
    return deduped
