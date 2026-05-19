import os
import json
import re
import html
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters


# ============================================================
# Setup
# ============================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_TELEGRAM_USER_ID = int(os.getenv("ALLOWED_TELEGRAM_USER_ID", "0"))
PUBLIC_BOT = os.getenv("PUBLIC_BOT", "false").lower() == "true"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
BOT_VERSION = "2026-05-15-vocab-tafsir-only-v2"

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# ============================================================
# Source settings
# ============================================================

TURATH_SEARCH_URL = "https://api.turath.io/search"
TURATH_PAGE_URL = "https://api.turath.io/page"

TURATH_CATEGORY_TAFSIR = 3
TURATH_CATEGORY_ARABIC_VOCAB_1 = 29
TURATH_CATEGORY_ARABIC_VOCAB_2 = 30
TURATH_LUGHA_CATEGORIES = [TURATH_CATEGORY_ARABIC_VOCAB_1, TURATH_CATEGORY_ARABIC_VOCAB_2]

# Preferred Turath tafsir books.
# These IDs are searched first for /tafsir and plain tafsir questions.
PREFERRED_TAFSIR_BOOK_IDS = [
    43,     # Tabari
    1503,   # Ibn Kathir
    23626,  # Ibn Juzayy
    20855,  # Qurtubi
    9776,   # Ibn Ashur
    18686,  # Tha'labi
    8346,   # Al-Mawardi
    13231,  # Al-Wahidi al-Baseet
    21821,  # Al-Wahidi al-Waseet
    41,     # Al-Baghawi
    1394,   # Al-Nasafi
    23627,  # Al-Zamakhshari
    23632,  # Ibn Atiyyah
    23619,  # Ibn al-Jawzi
    23635,  # Al-Razi
    23588,  # Al-Baydawi
    1429,   # Abu Su'ud
    22835,  # Al-Alusi
]

# Name aliases used to target a specific preferred tafsir book when the user names a mufassir.
# Keep aliases lowercase and include common spellings/transliterations.
PREFERRED_TAFSIR_AUTHOR_BOOKS = [
    {"label": "Al-Tabari", "book_ids": [43], "aliases": ["tabari", "al-tabari", "الطبري", "ابن جرير", "ibn jarir", "ibn jareer"]},
    {"label": "Ibn Kathir", "book_ids": [1503], "aliases": ["ibn kathir", "ibn katheer", "ابن كثير"]},
    {"label": "Ibn Juzayy", "book_ids": [23626], "aliases": ["ibn juzayy", "ibn juzyy", "ibn juzay", "ابن جزي", "ابن جزيّ"]},
    {"label": "Al-Qurtubi", "book_ids": [20855], "aliases": ["qurtubi", "al-qurtubi", "القرطبي"]},
    {"label": "Ibn Ashur", "book_ids": [9776], "aliases": ["ibn ashur", "ibn aashoor", "ibn ashour", "ibn 'ashur", "ابن عاشور"]},
    {"label": "Al-Tha'labi", "book_ids": [18686], "aliases": ["tha'labi", "thalabi", "al-thalabi", "الثعلبي"]},
    {"label": "Al-Mawardi", "book_ids": [8346], "aliases": ["mawardi", "al-mawardi", "الماوردي"]},
    {"label": "Al-Wahidi", "book_ids": [13231, 21821], "aliases": ["wahidi", "al-wahidi", "الواحدي"]},
    {"label": "Al-Baghawi", "book_ids": [41], "aliases": ["baghawi", "al-baghawi", "البغوي"]},
    {"label": "Al-Nasafi", "book_ids": [1394], "aliases": ["nasafi", "al-nasafi", "النسفي"]},
    {"label": "Al-Zamakhshari", "book_ids": [23627], "aliases": ["zamakhshari", "al-zamakhshari", "الزمخشري"]},
    {"label": "Ibn Atiyyah", "book_ids": [23632], "aliases": ["ibn atiyyah", "ibn atiya", "ibn 'atiyyah", "ابن عطية"]},
    {"label": "Ibn al-Jawzi", "book_ids": [23619], "aliases": ["ibn al-jawzi", "ibn jawzi", "ابن الجوزي"]},
    {"label": "Al-Razi", "book_ids": [23635], "aliases": ["razi", "al-razi", "fakhr al-din", "fakhruddin", "الرازي", "فخر الدين"]},
    {"label": "Al-Baydawi", "book_ids": [23588], "aliases": ["baydawi", "baydawee", "al-baydawi", "البيضاوي"]},
    {"label": "Abu Su'ud", "book_ids": [1429], "aliases": ["abu su'ud", "abu sa'ood", "أبو السعود"]},
    {"label": "Al-Alusi", "book_ids": [22835], "aliases": ["alusi", "al-alusi", "الآلوسي"]},
]

TAFSIR_APP_URL = "https://tafsir.app/get.php"
TAFSIR_APP_WORD_URL = "https://tafsir.app/get_word.php"

# tafsir.app sources for /verse.
TAFSIR_APP_SOURCES = [
    "muyassar",
    "mukhtasar",
    "saadi",
    "aysar-altafasir",
    "alaloosi",
    "alrazi",
    "ibn-aashoor",
    "ibn-atiyah",
    "tabari",
    "ibn-katheer",
    "qurtubi",
    "zad-almaseer",
    "almawirdee",
    "mathoor",
    "altasheel",
    "abu-alsuod",
    "nathm-aldurar",
    "mahasin-altaweel",
    "ibn-alqayyim",
    "alnasafi",
    "albaseet",
    "kashaf",
    "albaydawee",
]

TAFSIR_APP_SOURCE_LABELS = {
    "muyassar": "Al-Muyassar",
    "mukhtasar": "Al-Mukhtasar",
    "saadi": "Al-Sa‘di",
    "aysar-altafasir": "Aysar al-Tafasir",
    "alaloosi": "Al-Alusi",
    "alrazi": "Al-Razi",
    "ibn-aashoor": "Ibn ‘Ashur",
    "ibn-atiyah": "Ibn ‘Atiyyah",
    "tabari": "Al-Tabari",
    "ibn-katheer": "Ibn Kathir",
    "qurtubi": "Al-Qurtubi",
    "zad-almaseer": "Ibn al-Jawzi",
    "almawirdee": "Al-Mawardi",
    "mathoor": "Al-Tafsir al-Ma’thur",
    "altasheel": "Ibn Juzayy",
    "abu-alsuod": "Abu al-Su‘ud",
    "nathm-aldurar": "Al-Biqa‘i",
    "mahasin-altaweel": "Al-Qasimi",
    "ibn-alqayyim": "Ibn al-Qayyim",
    "alnasafi": "Al-Nasafi",
    "albaseet": "Al-Wahidi",
    "kashaf": "Al-Zamakhshari",
    "albaydawee": "Al-Baydawee",
}

# Quran.com tafsir sources for /verse.
QURAN_COM_TAFSIR_SOURCES = [
    {
        "source_id": "ar-tafsir-al-wasit",
        "source_name": "Al-Tafsir al-Wasit",
        "author": "Muhammad Sayyid Tantawi",
        "language": "arabic",
        "url_template": "https://quran.com/{surah}:{ayah}/tafsirs/ar-tafsir-al-wasit",
    },
    {
        "source_id": "en-tafsir-maarif-ul-quran",
        "source_name": "Ma‘arif al-Qur’an",
        "author": "Mufti Muhammad Shafi",
        "language": "english",
        "url_template": "https://quran.com/{surah}:{ayah}/tafsirs/en-tafsir-maarif-ul-quran",
    },
]

# tafsir.app vocabulary dictionaries for /vocab.
ARABIC_VOCAB_SOURCES = [
    "mufradat-ragheb",
    "lisan",
    "qamoos",
    "maqayees",
]

ARABIC_VOCAB_SOURCE_LABELS = {
    "mufradat-ragheb": "Mufradat al-Raghib",
    "lisan": "Lisan al-Arab",
    "qamoos": "Al-Qamus al-Muhit",
    "maqayees": "Maqayis al-Lughah",
}

REQUEST_TIMEOUT = 25
TURATH_MAX_RETRIES = 3
TURATH_BACKOFF_SECONDS = 1.5
TURATH_DELAY_BETWEEN_CALLS = 0.35

SEARCH_PER_QUERY_LIMIT = 5
SEARCH_MAX_TOTAL = 10
TURATH_CONTEXT_TOP_N = 5
TURATH_CONTEXT_RADIUS = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
}


# ============================================================
# Prompts
# ============================================================

SEARCH_QUERY_INSTRUCTIONS = """
You generate Arabic search queries for a Turath tafsir search bot.

The user may ask in Arabic or English. Return valid JSON only.
Produce 3 to 6 short Arabic search queries that would work well in classical tafsir books.
Do not answer the question.

JSON format:
{
  "language": "arabic" or "english",
  "queries": ["...", "..."]
}
"""

SOURCE_ONLY_ANSWER_INSTRUCTIONS = """
You are a private Islamic research assistant.

You may answer only from the approved source excerpts provided in the user's message.

Strict rules:
- Do not use outside knowledge.
- Do not guess.
- Do not issue fatwas.
- For tafsir, do not mention tafsir sources unless they are included in the approved excerpts.
- For Arabic vocabulary, answer only from the dictionary or lugha excerpts provided.
- If the excerpts do not contain enough information, say that you do not have enough information in the approved sources.
- If you refer to SOURCE 1, SOURCE 2, etc. in the body, that same source number must appear in the Sources used section.
- Always include a Sources used section.
- For tafsir.app sources, include source name, verse reference, and display link.
- For Quran.com sources, include source name, author, verse reference, and link.
- For vocabulary sources, include dictionary name, word, and display link.
- For Turath sources, include book name, author, volume, printed page, and link when available.

Language:
- If the user asked in Arabic, answer in Arabic.
- If the user asked in English, answer in English.

Style:
- Be concise and readable.
- Avoid heavy Markdown.
- Keep Telegram formatting clean.
"""


# ============================================================
# General helpers
# ============================================================

def is_allowed(update: Update) -> bool:
    if PUBLIC_BOT:
        return True
    user = update.effective_user
    return bool(user and user.id == ALLOWED_TELEGRAM_USER_ID)


def contains_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def detect_user_language(text: str) -> str:
    """
    Detect the language the user is asking in, not merely whether the query contains Arabic script.
    This lets '/vocab What does يوم mean?' answer in English while '/vocab ما معنى يوم؟' answers in Arabic.
    """
    text = text or ""
    english_letters = len(re.findall(r"[A-Za-z]", text))
    arabic_letters = len(re.findall(r"[\u0600-\u06FF]", text))

    english_cues = [
        "what does", "what is", "meaning of", "define", "definition", "in english",
        "translate", "explain", "lexical", "root meaning", "vocab", "vocabulary",
    ]
    arabic_cues = [
        "ما معنى", "معنى", "اشرح", "فسر", "تفسير", "ما المراد", "ما المقصود",
    ]

    lower = text.lower()
    if any(cue in lower for cue in english_cues):
        return "english"
    if any(cue in text for cue in arabic_cues) and english_letters == 0:
        return "arabic"
    if english_letters > 0 and english_letters >= max(3, arabic_letters // 2):
        return "english"
    return "arabic" if arabic_letters else "english"


def detect_tafsir_author_request(text: str) -> Optional[Dict[str, Any]]:
    lower = (text or "").lower()
    for author in PREFERRED_TAFSIR_AUTHOR_BOOKS:
        for alias in author["aliases"]:
            if alias in lower or alias in text:
                return author
    return None


def looks_like_vocab_question(text: str) -> bool:
    lower = (text or "").lower()
    vocab_cues = [
        "what does", "meaning of", "define", "definition", "lexical", "root meaning",
        "vocab", "vocabulary", "ما معنى", "معنى كلمة", "معنى", "اشرح كلمة",
        "مفردات", "لسان العرب", "مقاييس", "القاموس",
    ]
    return bool(extract_vocab_word(text)) and any(cue in lower or cue in text for cue in vocab_cues)


def looks_like_verse_question(text: str) -> bool:
    surah, ayah = extract_verse_reference(text)
    if not is_valid_verse_reference(surah, ayah):
        return False
    lower = (text or "").lower()
    return any(cue in lower or cue in text for cue in ["verse", "ayah", "tafsir", "explain", "تفسير", "آية", "اية", "معنى"]) or bool(re.search(r"\b\d{1,3}\s*[:/]\s*\d{1,3}\b", text or ""))


def strip_html(raw: Optional[str]) -> str:
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(" ", strip=True)
    return html.unescape(text)


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_turath_footnotes(text: str) -> str:
    if not text:
        return ""
    for sep in ["_________", "__________", "____________", "ــــــــــــ", "________________"]:
        if sep in text:
            return text.split(sep, 1)[0].strip()
    return text.strip()


def truncate_text(text: str, max_chars: int = 2500) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def telegram_safe_chunks(text: str, limit: int = 3900) -> List[str]:
    if len(text) <= limit:
        return [text]

    chunks: List[str] = []
    current = ""
    for paragraph in text.split("\n"):
        if len(current) + len(paragraph) + 1 <= limit:
            current += paragraph + "\n"
        else:
            if current.strip():
                chunks.append(current.strip())
            current = paragraph + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


def safe_json_loads(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text or "", re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def normalize_arabic_word(word: str) -> str:
    word = (word or "").strip()
    word = re.sub(r"[^\u0600-\u06FFء-يآأإؤئاةى]+", "", word)
    return word.strip()


def extract_vocab_word(raw: str) -> Optional[str]:
    raw = raw.strip()
    patterns = [
        r"ما\s+معنى\s+([ء-يآأإؤئاةى]+)",
        r"معنى\s+كلمة\s+([ء-يآأإؤئاةى]+)",
        r"معنى\s+([ء-يآأإؤئاةى]+)",
        r"meaning of\s+([ء-يآأإؤئاةى]+)",
        r"what does\s+([ء-يآأإؤئاةى]+)\s+mean",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            word = normalize_arabic_word(match.group(1))
            if word:
                return word

    words = re.findall(r"[ء-يآأإؤئاةى]+", raw)
    if len(words) == 1:
        return normalize_arabic_word(words[0])
    return normalize_arabic_word(words[-1]) if words else None


def extract_verse_reference(raw: str) -> Tuple[Optional[int], Optional[int]]:
    raw = raw.strip()

    match = re.search(r"\b(\d{1,3})\s*[:/]\s*(\d{1,3})\b", raw)
    if match:
        surah = int(match.group(1))
        ayah = int(match.group(2))
        if 1 <= surah <= 114 and ayah >= 1:
            return surah, ayah

    match = re.search(
        r"(?:surah|sura|chapter|سورة)\s*(\d{1,3}).{0,25}?(?:ayah|aya|verse|آية|ايه|آيه)\s*(\d{1,3})",
        raw,
        re.IGNORECASE,
    )
    if match:
        surah = int(match.group(1))
        ayah = int(match.group(2))
        if 1 <= surah <= 114 and ayah >= 1:
            return surah, ayah

    return None, None


def is_valid_verse_reference(surah: Optional[int], ayah: Optional[int]) -> bool:
    return isinstance(surah, int) and isinstance(ayah, int) and 1 <= surah <= 114 and ayah >= 1


def format_book_ids(book_ids: List[int]) -> str:
    unique_ids: List[int] = []
    seen = set()
    for book_id in book_ids:
        if book_id not in seen:
            seen.add(book_id)
            unique_ids.append(book_id)
    return ",".join(str(x) for x in unique_ids)


# ============================================================
# Turath search + context expansion
# ============================================================

def turath_request_json(url: str, params: Dict[str, Any], label: str) -> Optional[Dict[str, Any]]:
    for attempt in range(TURATH_MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                time.sleep(TURATH_DELAY_BETWEEN_CALLS)
                return response.json()

            logging.warning("%s returned status %s: %s", label, response.status_code, response.url)
            if response.status_code in [429, 500, 502, 503, 504]:
                time.sleep(TURATH_BACKOFF_SECONDS * (attempt + 1))
                continue
            response.raise_for_status()
        except Exception as exc:
            logging.warning("%s failed on attempt %s/%s: %s", label, attempt + 1, TURATH_MAX_RETRIES, exc)
            if attempt < TURATH_MAX_RETRIES - 1:
                time.sleep(TURATH_BACKOFF_SECONDS * (attempt + 1))
            else:
                logging.exception("%s final failure", label)
                return None
    return None


def parse_turath_meta(meta_raw: Any) -> Dict[str, Any]:
    if isinstance(meta_raw, dict):
        return meta_raw
    try:
        return json.loads(meta_raw or "{}")
    except Exception:
        return {}


def search_turath(
    query: str,
    limit: int = SEARCH_PER_QUERY_LIMIT,
    precision: int = 2,
    cat_id: Optional[int] = None,
    book_ids: Optional[List[int]] = None,
    source_scope: str = "turath",
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "ver": 3,
        "q": query,
        "non_author": 1,
        "precision": precision,
    }

    if book_ids:
        params["book"] = format_book_ids(book_ids)
    elif cat_id:
        params["cat"] = cat_id
    else:
        raise ValueError("search_turath requires either book_ids or cat_id")

    payload = turath_request_json(TURATH_SEARCH_URL, params, "Turath search API")
    if not payload:
        return []

    results: List[Dict[str, Any]] = []
    for item in payload.get("data", [])[:limit]:
        meta = parse_turath_meta(item.get("meta", "{}"))
        book_id = item.get("book_id")
        page_id = meta.get("page_id")
        url = f"https://app.turath.io/book/{book_id}?page={page_id}" if book_id and page_id else None

        results.append(
            {
                "source_type": "turath",
                "source_scope": source_scope,
                "query": query,
                "book_id": book_id,
                "cat_id": item.get("cat_id"),
                "author_id": item.get("author_id"),
                "book_name": meta.get("book_name", ""),
                "author_name": meta.get("author_name", ""),
                "vol": str(meta.get("vol", "")),
                "page": str(meta.get("page", "")),
                "page_id": str(page_id or ""),
                "headings": meta.get("headings", []),
                "snip": remove_turath_footnotes(strip_html(item.get("snip"))),
                "text": remove_turath_footnotes(strip_html(item.get("text"))),
                "url": url,
            }
        )
    return results


def fetch_turath_page(book_id: int, page_id: int) -> Optional[Dict[str, Any]]:
    payload = turath_request_json(
        TURATH_PAGE_URL,
        {"book_id": book_id, "pg": page_id},
        "Turath page API",
    )
    if not payload:
        return None

    meta = parse_turath_meta(payload.get("meta", "{}"))
    text = remove_turath_footnotes(strip_html(payload.get("text", "")))
    if not text:
        return None

    return {
        "book_id": book_id,
        "page_id": page_id,
        "printed_page": str(meta.get("page", "")),
        "vol": str(meta.get("vol", "")),
        "book_name": meta.get("book_name", ""),
        "author_name": meta.get("author_name", ""),
        "url": f"https://app.turath.io/book/{book_id}?page={page_id}",
        "text": text,
    }


def expand_turath_context(results: List[Dict[str, Any]], top_n: int = TURATH_CONTEXT_TOP_N, radius: int = TURATH_CONTEXT_RADIUS) -> List[Dict[str, Any]]:
    expanded: List[Dict[str, Any]] = []
    cache: Dict[Tuple[int, int], Optional[Dict[str, Any]]] = {}
    turath_count = 0

    for result in results:
        if result.get("source_type") != "turath":
            expanded.append(result)
            continue

        turath_count += 1
        if turath_count > top_n:
            expanded.append(result)
            continue

        try:
            book_id = int(result.get("book_id"))
            center_page_id = int(result.get("page_id"))
        except Exception:
            expanded.append(result)
            continue

        pages: List[Dict[str, Any]] = []
        for page_id in range(center_page_id - radius, center_page_id + radius + 1):
            if page_id < 1:
                continue
            key = (book_id, page_id)
            if key not in cache:
                cache[key] = fetch_turath_page(book_id, page_id)
            if cache[key]:
                pages.append(cache[key])

        if not pages:
            expanded.append(result)
            continue

        combined_text = []
        for page in pages:
            combined_text.append(
                f"[page_id {page.get('page_id')}, printed page {page.get('printed_page')}, volume {page.get('vol')}]\n{page.get('text')}"
            )

        new_result = dict(result)
        new_result["expanded_context"] = True
        new_result["expanded_pages"] = pages
        new_result["text"] = "\n\n".join(combined_text)
        expanded.append(new_result)

    return expanded


def add_unique(destination: List[Dict[str, Any]], new_results: List[Dict[str, Any]], seen: set, max_total: int) -> bool:
    for result in new_results:
        if result.get("source_type") == "turath":
            key = ("turath", result.get("book_id"), result.get("page_id"), result.get("text", "")[:80])
        else:
            key = (result.get("source_type"), result.get("source_id"), result.get("url"))

        if key in seen:
            continue
        seen.add(key)
        destination.append(result)
        if len(destination) >= max_total:
            return True
    return False


def search_turath_books_layer(queries: List[str], book_ids: List[int], scope: str) -> List[Dict[str, Any]]:
    all_results: List[Dict[str, Any]] = []
    seen = set()
    for query in queries:
        results = search_turath(query=query, book_ids=book_ids, source_scope=scope)
        if add_unique(all_results, results, seen, SEARCH_MAX_TOTAL):
            break
    return all_results


def search_turath_category_layer(queries: List[str], cat_id: int, scope: str) -> List[Dict[str, Any]]:
    all_results: List[Dict[str, Any]] = []
    seen = set()
    for query in queries:
        results = search_turath(query=query, cat_id=cat_id, source_scope=scope)
        if add_unique(all_results, results, seen, SEARCH_MAX_TOTAL):
            break
    return all_results


# ============================================================
# tafsir.app, Quran.com, and vocab retrieval
# ============================================================

def fetch_tafsir_app_source(source_id: str, surah: int, ayah: int) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(
            TAFSIR_APP_URL,
            params={"src": source_id, "s": surah, "a": ayah},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        logging.exception("tafsir.app source fetch failed: %s %s:%s", source_id, surah, ayah)
        return None

    data = payload.get("data", "")
    if not data:
        return None

    return {
        "source_type": "tafsir_app",
        "source_scope": "tafsir_app_specific_verse",
        "source_id": source_id,
        "source_name": TAFSIR_APP_SOURCE_LABELS.get(source_id, source_id),
        "surah_number": surah,
        "ayah_number": ayah,
        "ayah_text": payload.get("ayah", ""),
        "text": strip_html(data),
        "url": f"https://tafsir.app/{source_id}/{surah}/{ayah}",
    }


def remove_noise_from_soup(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "button", "form"]):
        tag.decompose()


def extract_quran_com_tafsir_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    remove_noise_from_soup(soup)
    lines = [clean_text(line) for line in soup.get_text("\n", strip=True).splitlines()]
    noise = {
        "Quran.com",
        "Settings",
        "Donate",
        "Support Quran.com",
        "Read Quran",
        "Developers",
        "Privacy",
        "Terms",
        "Translation",
        "Transliteration",
        "Reciter",
        "The Noble Quran",
        "Navigate",
        "Surah",
        "Ayah",
    }
    lines = [line for line in lines if line and line not in noise and len(line) >= 5]
    return "\n".join(lines)


def fetch_quran_com_tafsir_source(source: Dict[str, str], surah: int, ayah: int) -> Optional[Dict[str, Any]]:
    url = source["url_template"].format(surah=surah, ayah=ayah)
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        text = extract_quran_com_tafsir_text(response.text)
    except Exception:
        logging.exception("Quran.com tafsir fetch failed: %s", url)
        return None

    if not text:
        return None

    return {
        "source_type": "quran_com_tafsir",
        "source_scope": "quran_com_specific_verse",
        "source_id": source["source_id"],
        "source_name": source["source_name"],
        "author": source.get("author", ""),
        "language": source.get("language", ""),
        "surah_number": surah,
        "ayah_number": ayah,
        "text": text,
        "url": url,
    }


def collect_verse_results(surah: int, ayah: int) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for source_id in TAFSIR_APP_SOURCES:
        result = fetch_tafsir_app_source(source_id, surah, ayah)
        if result:
            results.append(result)

    for source in QURAN_COM_TAFSIR_SOURCES:
        result = fetch_quran_com_tafsir_source(source, surah, ayah)
        if result:
            results.append(result)

    return results


def fetch_vocab_source(source_id: str, word: str) -> Optional[Dict[str, Any]]:
    if not word:
        return None

    try:
        response = requests.get(
            TAFSIR_APP_WORD_URL,
            params={"src": source_id, "w": word},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        logging.exception("tafsir.app word fetch failed: %s %s", source_id, word)
        return None

    data = payload.get("data", "")
    if not data:
        return None

    encoded_word = quote(word)
    return {
        "source_type": "arabic_vocab",
        "source_scope": "tafsir_app_dictionary",
        "source_id": source_id,
        "source_name": ARABIC_VOCAB_SOURCE_LABELS.get(source_id, source_id),
        "word": word,
        "text": strip_html(data),
        "url": f"https://tafsir.app/{source_id}/{encoded_word}",
    }


def collect_vocab_results(word: str) -> Tuple[List[Dict[str, Any]], str]:
    dictionary_results: List[Dict[str, Any]] = []
    for source_id in ARABIC_VOCAB_SOURCES:
        result = fetch_vocab_source(source_id, word)
        if result:
            dictionary_results.append(result)

    if dictionary_results:
        return dictionary_results, "tafsir.app dictionaries"

    turath_results: List[Dict[str, Any]] = []
    seen = set()
    for cat_id in TURATH_LUGHA_CATEGORIES:
        results = search_turath_category_layer(
            queries=[word],
            cat_id=cat_id,
            scope=f"turath_lugha_category_{cat_id}_fallback",
        )
        add_unique(turath_results, results, seen, SEARCH_MAX_TOTAL)

    return turath_results, "Turath lugha fallback categories 29 and 30"


# ============================================================
# OpenAI query and answer generation
# ============================================================

def generate_search_queries(question: str) -> Dict[str, Any]:
    fallback_language = "arabic" if contains_arabic(question) else "english"
    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=SEARCH_QUERY_INSTRUCTIONS,
            input=f"User question:\n{question}",
        )
    except Exception:
        logging.exception("OpenAI query generation failed")
        return {"language": fallback_language, "queries": [question]}

    parsed = safe_json_loads(response.output_text)
    if not parsed:
        return {"language": fallback_language, "queries": [question]}

    queries = [q.strip() for q in parsed.get("queries", []) if isinstance(q, str) and q.strip()]
    if not queries:
        queries = [question]

    language = parsed.get("language", fallback_language)
    if language not in ["arabic", "english"]:
        language = fallback_language

    return {"language": language, "queries": queries[:6]}


def build_source_packet(results: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for idx, result in enumerate(results, start=1):
        source_type = result.get("source_type")

        if source_type == "tafsir_app":
            parts.append(
                f"""
SOURCE {idx}
Source type: tafsir.app
Source name: {result.get('source_name')}
Verse: {result.get('surah_number')}:{result.get('ayah_number')}
Link: {result.get('url')}
Ayah text:
{truncate_text(result.get('ayah_text', ''), 1000)}

Text:
{truncate_text(result.get('text', ''), 3000)}
""".strip()
            )
            continue

        if source_type == "quran_com_tafsir":
            parts.append(
                f"""
SOURCE {idx}
Source type: Quran.com tafsir
Source name: {result.get('source_name')}
Author: {result.get('author')}
Language: {result.get('language')}
Verse: {result.get('surah_number')}:{result.get('ayah_number')}
Link: {result.get('url')}

Text:
{truncate_text(result.get('text', ''), 3000)}
""".strip()
            )
            continue

        if source_type == "arabic_vocab":
            parts.append(
                f"""
SOURCE {idx}
Source type: tafsir.app dictionary
Dictionary: {result.get('source_name')}
Word: {result.get('word')}
Link: {result.get('url')}

Text:
{truncate_text(result.get('text', ''), 3000)}
""".strip()
            )
            continue

        headings = result.get("headings") or []
        headings_text = " > ".join(str(h) for h in headings)

        expanded_pages_text = ""
        if result.get("expanded_context") and result.get("expanded_pages"):
            page_refs = []
            for page in result.get("expanded_pages", []):
                page_refs.append(
                    f"page_id {page.get('page_id')} / printed page {page.get('printed_page')} / vol {page.get('vol')}"
                )
            expanded_pages_text = "\nExpanded pages: " + "; ".join(page_refs)

        parts.append(
            f"""
SOURCE {idx}
Source type: Turath
Source scope: {result.get('source_scope')}
Query matched: {result.get('query')}
Book: {result.get('book_name')}
Author: {result.get('author_name')}
Volume: {result.get('vol')}
Printed page: {result.get('page')}
Turath page_id: {result.get('page_id')}
Link: {result.get('url')}
Headings: {headings_text}{expanded_pages_text}

Snippet:
{truncate_text(result.get('snip', ''), 700)}

Text:
{truncate_text(result.get('text', ''), 6000 if result.get('expanded_context') else 2500)}
""".strip()
        )

    return "\n\n---\n\n".join(parts)


def answer_from_sources(question: str, results: List[Dict[str, Any]], detected_language: str, mode_note: str) -> str:
    if not results:
        if detected_language == "arabic" or contains_arabic(question):
            return "لم أجد معلومات كافية في المصادر المعتمدة للإجابة عن هذا السؤال."
        return "I do not have enough information in the approved sources to answer that."

    source_packet = build_source_packet(results)
    user_message = f"""
User question:
{question}

Detected user language:
{detected_language}

Retrieval mode:
{mode_note}

Approved source excerpts:
{source_packet}

Answer using only the approved source excerpts.
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=SOURCE_ONLY_ANSWER_INSTRUCTIONS,
            input=user_message,
        )
        return response.output_text.strip()
    except Exception:
        logging.exception("OpenAI answer generation failed")
        if detected_language == "arabic" or contains_arabic(question):
            return "حدث خطأ أثناء توليد الجواب. حاول مرة أخرى."
        return "There was an error generating the answer. Please try again."


# ============================================================
# Command processors
# ============================================================

async def send_chunks(update: Update, text: str) -> None:
    for chunk in telegram_safe_chunks(text):
        await update.message.reply_text(chunk)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await update.message.reply_text("This bot is private.")
        return

    msg = (
        "Tafsir and Vocabulary Research Bot is ready.\n\n"
        "Commands:\n\n"
        "/vocab [Arabic word] - searches tafsir.app dictionaries first; if none found, falls back to Turath general lugha categories.\n\n"
        "/verse [surah:ayah] - searches tafsir.app and Quran.com tafsir sources only for a specific verse.\n\n"
        "/tafsir [question/keywords] - searches preferred tafsir books first; if none found, falls back to Turath tafsir category.\n\n"
        "You don't have to use the above commands. You can ask questions naturally as well and it will determine where to send it based on the question.\n\n"
        "Examples:\n\n"
        "/vocab يوم\n\n"
        "/vocab what is the meaning of صراط\n\n"
        "/verse What is the tafsir of 1:4\n\n"
        "/verse What did Qurtubi say about 1:4\n\n"
        "/tafsir معنى الصراط المستقيم\n\n"
        "/tafsir What did Ibn Ashur say about the concept of worship\n\n"
        "/tafsir How did mufassirs understand the verse about..."
    )
    await update.message.reply_text(msg)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(f"Your Telegram user ID is: {user.id}")


async def vocab_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await update.message.reply_text("This bot is private.")
        return

    raw = " ".join(context.args).strip()
    if not raw:
        await update.message.reply_text("Use: /vocab يوم")
        return

    await process_vocab_lookup(update, raw)


async def process_vocab_lookup(update: Update, raw: str) -> None:
    word = extract_vocab_word(raw)
    if not word:
        await update.message.reply_text("Please include the Arabic word you want to look up. Example: /vocab يوم")
        return

    await update.message.chat.send_action(action=ChatAction.TYPING)
    await update.message.reply_text("Searching vocabulary sources...")

    results, layer_used = collect_vocab_results(word)
    if layer_used.startswith("Turath"):
        results = expand_turath_context(results)

    language = detect_user_language(raw)
    question = (
        f"What does the Arabic word {word} mean in the approved Arabic vocabulary sources? User wording: {raw}"
        if language == "english"
        else f"ما معنى كلمة {word} في مصادر اللغة العربية؟ صيغة سؤال المستخدم: {raw}"
    )
    answer = answer_from_sources(question, results, language, layer_used)
    await send_chunks(update, answer)


async def verse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await update.message.reply_text("This bot is private.")
        return

    raw = " ".join(context.args).strip()
    if not raw:
        await update.message.reply_text("Use: /verse 1:4")
        return

    await process_verse_lookup(update, raw)


async def process_verse_lookup(update: Update, raw: str) -> None:
    surah, ayah = extract_verse_reference(raw)
    if not is_valid_verse_reference(surah, ayah):
        await update.message.reply_text("Please include a verse reference like /verse 1:4")
        return

    await update.message.chat.send_action(action=ChatAction.TYPING)
    await update.message.reply_text("Searching tafsir.app and Quran.com verse tafsir sources...")

    results = collect_verse_results(surah, ayah)
    language = detect_user_language(raw)
    question = f"Give tafsir for Quran {surah}:{ayah}. User wording: {raw}"
    answer = answer_from_sources(question, results, language, "tafsir.app + Quran.com specific verse sources")
    await send_chunks(update, answer)


async def tafsir_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await update.message.reply_text("This bot is private.")
        return

    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text("Use: /tafsir معنى الصراط المستقيم")
        return

    await process_tafsir_search(update, question)


async def process_tafsir_search(update: Update, question: str) -> None:
    await update.message.chat.send_action(action=ChatAction.TYPING)

    author = detect_tafsir_author_request(question)
    if author:
        await update.message.reply_text(f"Searching {author['label']} on Turath...")
    else:
        await update.message.reply_text("Searching preferred Turath tafsir books first...")

    query_info = generate_search_queries(question)
    queries = query_info.get("queries", [question])
    language = detect_user_language(question)

    if author:
        results = search_turath_books_layer(
            queries=queries,
            book_ids=author["book_ids"],
            scope=f"specific_mufassir_{author['label']}_turath_books",
        )
        layer_used = f"specific mufassir: {author['label']}"
    else:
        results = search_turath_books_layer(
            queries=queries,
            book_ids=PREFERRED_TAFSIR_BOOK_IDS,
            scope="preferred_turath_tafsir_books",
        )
        layer_used = "preferred Turath tafsir books"

    if not results and not author:
        await update.message.reply_text("No preferred-book hits found. Falling back to the general Turath tafsir category...")
        results = search_turath_category_layer(
            queries=queries,
            cat_id=TURATH_CATEGORY_TAFSIR,
            scope="general_turath_tafsir_category_fallback",
        )
        layer_used = "general Turath tafsir category 3 fallback"

    results = expand_turath_context(results)
    answer = answer_from_sources(question, results, language, layer_used)
    await send_chunks(update, answer)


async def plain_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await update.message.reply_text("This bot is private.")
        return

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Please send a question.")
        return

    if looks_like_vocab_question(text):
        await process_vocab_lookup(update, text)
        return

    if looks_like_verse_question(text):
        await process_verse_lookup(update, text)
        return

    await process_tafsir_search(update, text)


# ============================================================
# Main app
# ============================================================

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env")
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")
    if not PUBLIC_BOT and not ALLOWED_TELEGRAM_USER_ID:
        raise RuntimeError("Missing or invalid ALLOWED_TELEGRAM_USER_ID in .env")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("vocab", vocab_command))
    app.add_handler(CommandHandler("verse", verse_command))
    app.add_handler(CommandHandler("tafsir", tafsir_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_message))

    print("Tafsir and Vocabulary Research Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
