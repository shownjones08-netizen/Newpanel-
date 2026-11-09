#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          SHOWN X PANEL BOT — v3.1 ULTRA EDITION             ║
║   OTP Panel + ShownStore DNA + Live Monitor + User Hub       ║
║   Clone Manager + Firebase Health + Customize Studio         ║
║                                                              ║
║   v3.1 — Button Engine Fix                                   ║
║     • Reply keyboard labels never stylized (routing works)   ║
║     • Colored keyboards: primary/success/danger              ║
║     • Hash-based DB callback tags (no 64-byte overflow)      ║
║     • PTB 22.5 / 22.8+ style compat via api_kwargs           ║
║     • PREMIUM_EMOJI_BUTTONS flag (safe default: off)         ║
╚══════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import html
import inspect as _inspect_ptb
import io
import json
import logging
import os
import re
import random
import sqlite3
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiohttp

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
)
try:
    from telegram import CopyTextButton as _PTB_COPY_TEXT_BUTTON
except ImportError:
    _PTB_COPY_TEXT_BUTTON = None

from telegram.constants import ParseMode
from telegram.error import (
    BadRequest, Forbidden, RetryAfter, TelegramError, Conflict, ChatMigrated
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

BOT_TOKEN        = os.environ["BOT_TOKEN"]            # hard fail — no fallback
BOT_USERNAME     = os.environ.get("BOT_USERNAME", "@shownXpannelbot")
BOT_BRAND_NAME   = os.environ.get("BOT_BRAND_NAME", "QURESHIxOTP")
OWNER_DISPLAY    = os.environ.get("OWNER_DISPLAY_NAME", "Shown")
OWNER_CONTACT    = os.environ.get("OWNER_CONTACT", "@WhoIsShown")
OWNER_ID         = int(os.environ.get("OWNER_ID", "8984851474"))
OWNER_USERNAME   = "WhoIsShown"

SQLITE_DB_PATH   = "shownxpanel.db"
BOT_VERSION      = "v3.1-ultra"
RICH_MESSAGES_ENABLED = True
HEALTH_CHECK_PORT     = 10000

POLL_INTERVAL    = 15
SMS_LIMIT        = 10
DB_CONCURRENCY   = 50
MAX_SEEN_IDS     = 200_000

FB_HEALTH_INTERVAL = 300

# ── Global toggle: premium emoji as inline-button icons ───────
# True  → bot tries icon_custom_emoji_id on buttons
#         (only works if bot owner has Telegram Premium — otherwise
#          Telegram rejects the WHOLE keyboard with BadRequest)
# False → plain buttons. Safe on every account. This is default.
PREMIUM_EMOJI_BUTTONS = False

PANEL_QUOTES = [
    "⚡ Speed is the soul of the hustle.",
    "🔥 Every OTP is a door — we open them all.",
    "🧬 Data flows where the rat goes.",
    "💎 Quality panel, premium results.",
    "🚀 Built in the walls, shipped before dawn.",
    "🎯 Precision first. Volume second.",
    "⚓ Grounded. Sharp. Always online.",
    "🌪 The storm doesn't stop the signal.",
]

# ══════════════════════════════════════════════════════════════
#  DEFAULT FIREBASE DATABASES
# ══════════════════════════════════════════════════════════════

DEFAULT_DATABASES: dict[str, str] = {
    "👑 BOSS_R1":        "https://rexxx-4c7a7-default-rtdb.firebaseio.com",
    "👑 BOSS_R2":        "https://runjun-master-panel-default-rtdb.firebaseio.com",
    "⚡ ALPHA_A2":       "https://rto9-d2b33-default-rtdb.firebaseio.com",
    "🔥 ALPHA_A5":       "https://challan-758d1-default-rtdb.asia-southeast1.firebasedatabase.app",
    "⚔️ ALPHA_A12":      "https://fir-1fa16-default-rtdb.firebaseio.com",
    "🎯 ALPHA_A19":      "https://u40179853-987df-default-rtdb.firebaseio.com",
    "🔫 ALPHA_A21":      "https://u62803313-e54bc-default-rtdb.firebaseio.com",
    "🦾 ALPHA_A24":      "https://u67583339-bf0c1-default-rtdb.firebaseio.com",
    "🏹 ALPHA_A27":      "https://u8208372-ad1d1-default-rtdb.firebaseio.com",
    "🌪 ALPHA_A29":      "https://u25428732-91bd9-default-rtdb.firebaseio.com",
    "💥 ALPHA_A31":      "https://u72749819-fa563-default-rtdb.firebaseio.com",
    "🩸 ALPHA_A32":      "https://u24143844-c1b11-default-rtdb.firebaseio.com",
    "👹 ALPHA_A33":      "https://u72328193-47b68-default-rtdb.firebaseio.com",
    "🎭 ALPHA_A34":      "https://u58325342-dffc0-default-rtdb.firebaseio.com",
    "⛓ ALPHA_A35":      "https://u75887828-b5a63-default-rtdb.firebaseio.com",
    "🧿 ALPHA_A36":      "https://u24153206-5eef6-default-rtdb.firebaseio.com",
    "💵 MAFIA_M7":       "https://rto-47-b39f4-default-rtdb.firebaseio.com",
    "💰 MAFIA_M15_1":    "https://chfjfj-c2857-default-rtdb.firebaseio.com",
    "💎 MAFIA_M15_2":    "https://ai-rto-9-default-rtdb.firebaseio.com",
    "✨ VIP_EXTRA":      "https://s85138920-87594-default-rtdb.firebaseio.com",
    "📦 FORTY_DATA":     "https://fortydata-fee65-default-rtdb.firebaseio.com",
    "📡 FPRO_INDUS":     "https://fpro3indus-default-rtdb.firebaseio.com",
    "🚨 JAMTARA_181":    "https://jamtara181-default-rtdb.firebaseio.com",
    "🛸 PMS_JDJ":        "https://pmsjdj-default-rtdb.firebaseio.com",
    "💻 MY_CARRY":       "https://cs6mycarry68jh-default-rtdb.firebaseio.com",
    "🃏 RANDI_RONA":     "https://randi-rona-81876-default-rtdb.firebaseio.com",
    "🚔 RTO_CHALLAN_A":  "https://rtochallan-8579d-default-rtdb.firebaseio.com",
    "🛑 RTO_CHALLAN_B":  "https://rtochallan8-default-rtdb.firebaseio.com",
    "🐾 JAMTARA_140":    "https://jamtaar140-73bf7-default-rtdb.firebaseio.com",
    "🔮 GGGGGG_NODE":    "https://gggggg-979bd-default-rtdb.firebaseio.com",
    "⚡ SHOWN SPECIAL":  "https://flash-v8enginepower-default-rtdb.firebaseio.com",
}

# ══════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
log = logging.getLogger("SHOWNX_PANEL")

# ══════════════════════════════════════════════════════════════
#  PREMIUM EMOJI ENGINE
# ══════════════════════════════════════════════════════════════

_PREMIUM_EMOJI_IDS_1 = [
    "5967280668885913944","5258476306152038031","5213395028038132311","5260342697075416641",
    "5258236805890710909","5260450573768990626","5429571366384842791","5956561916573782596",
    "5870930636742595124","5956561916573782596","5258514780469075716","5359719332542718652",
    "5463274047771000031","5282964865349081926","5418010521309815154","5372917041193828849",
    "5870930636742595124","5260379144167890225","6280818246476111911","6111547907393987376",
    "5199552030615558774","6235403472741603087","5384544226333711035","6098159343281121498",
    "6319074379175043387","5445355530111437729","5258514780469075716","6100129320225741245",
    "6100384016081361171","6098236364929635183","5453957997418004470","5462921117423384478",
    "6280578093379754919","5416081784641168838","6100388225149310843","5244837092042750681",
    "5258477770735885832","5375464961822695044","5359529383319084413","5257974976094412956",
    "6201822626692734126","5897850551156084824","6005986106703613755","6203998186541948045",
    "6278463693864838049","5416081784641168838","5213395028038132311","6100258190719457801",
    "6100670735213139506","6098125829651307984","6219792052599660507","5409008750893734809",
    "6269400956387987689","5447203607294265305","5453902265922376865","5377599075237502153",
    "5915833712368424979","5415722218569089767","5197480146981906157","5388846172951558229",
    "5305336095863485125","5388941018714356665","6319074379175043387","5305603955793867793",
    "5280816565657300091",
]

_PREMIUM_EMOJI_LIST_1 = [
    "\u2709\ufe0f","\U0001f512","\u2705","\u274c","\u2b05\ufe0f","\u27a1\ufe0f","\U0001f50e",
    "\U0001f4c4","\U0001f4ca","\U0001f4c4","\U0001f4c2","\U0001f48e","\U0001f635","\U0001f49d",
    "\U0001f3ab","\U0001f680","\U0001f4ca","\U0001f53c","\U0001f4ac","\U0001f451",
    "\U0001fa99","\u2b50","\U0001f381","\U0001f4b0","\U0001f48e","\U0001f4e4","\U0001f4c2",
    "\U0001f6e1","\U0001f381","\U0001f4e2","\U0001f465","\U0001f6e0","\u2699\ufe0f",
    "\U0001f7e2","\U0001f6ab","\U0001f4c8","\U0001f4c4","\U0001f3ac","\u2795","\U0001f5bc",
    "\U0001f399","\U0001f4d6","\U0001f4f7","\U0001f451","\u2b50\ufe0f","\U0001f7e2","\u2705",
    "\U0001f534","\U0001f7e2","\U0001f389","\U0001f525","\U0001f3c6","\U0001f947","\U0001f948",
    "\U0001f949","\U0001f39f","\U0001f3b0","\U0001f352","\U0001f34b\u200d\U0001f7e9",
    "\U0001f347","\U0001f349","\U0001f34a","\U0001f48e","7\ufe0f\u20e3","\U0001f3b2",
]

_PREMIUM_EMOJI_IDS_2 = [
    "5418010521309815154","5258500400918587241","5451732530048802485","6332591195306334733",
    "6280368657889501500","5888781182249738113","6280648681167266267","6111396350883010682",
    "5258205968025525531","5444856076954520455","5258134813302332906","5350460637182993292",
    "5803057229909202251","6280712659000107348","5258331647358540449","5870930744116776638",
    "6221832909389570589","6098271033905650109","5447203607294265305","5453902265922376865",
    "6222239449518971912","5458603043203327669","6203974332293586380","5260502250815513613",
    "6172537761552142514","5280774071250872500","5384490809825450636","6278178593935728769",
    "6098271033905650109","6323166881712709901","6203957491726818885","5846210329700217522",
    "5258476306152038031","5258476306152038031","6334528491844798409","5462990652943904884",
    "6280289450102628695","5197434882321567830","5469641199348363998","5445353829304387411",
    "5444856076954520455","6280368657889501500","6203998186541948045","5188187560035234546",
    "6100670735213139506",
]

_PREMIUM_EMOJI_LIST_2 = [
    "\U0001f3ab","\u270d\ufe0f","\u23f3","\U0001f51c","\U0001f464","\U0001f194","\U0001f4c5",
    "\u26d3","\U0001f4f8","\U0001f9fe","\U0001f4e6","\U0001f3af","\u267b\ufe0f","\U0001f5d1",
    "\u270d\ufe0f","\U0001f4cc","\U0001f31f","\U0001f947","\U0001f948","\U0001f949",
    "\u26a1\ufe0f","\U0001f514","\U0001f38a","\U0001f973","\U0001f340","\U0001f37e","\U0001f381",
    "\U0001f6e1","\U0001f947","\U0001f948","\u2705","\u274c","\u26a0\ufe0f","\U0001f512",
    "\U0001f513","\U0001f477","\U0001f634","\U0001f4b0","\U0001f4b5","\u2b50\ufe0f",
    "\U0001f4b3","\U0001f9fe","\U0001f464","\U0001f451","\u26d4\ufe0f",
]

PREMIUM_EMOJI_MAP: dict[str, str] = {}
for _emj, _eid in list(zip(_PREMIUM_EMOJI_LIST_1, _PREMIUM_EMOJI_IDS_1)) + list(
    zip(_PREMIUM_EMOJI_LIST_2, _PREMIUM_EMOJI_IDS_2)
):
    PREMIUM_EMOJI_MAP.setdefault(_emj, _eid)

for _emj, _eid in list(PREMIUM_EMOJI_MAP.items()):
    _plain = _emj.replace("\ufe0f", "")
    if _plain and _plain != _emj:
        PREMIUM_EMOJI_MAP.setdefault(_plain, _eid)
    PREMIUM_EMOJI_MAP.setdefault(_emj + "\ufe0f", _eid)

_EXTRA = {
    "\U0001f4b8": "5404561694510833322",
    "\U0001f50d": "6206446249181189526",
    "\U0001f4af": "5206318837489743801",
    "\u2604":     "5224607267797606837",
    "\u26d4":     "5246772116543512028",
    "\u270b":     "5339286072876614251",
    "\U0001f6f8": "5372849966689566579",
    "\u270f":     "6204162490515855272",
    "\U0001f517": "6206497372176913599",
    "\u2b50":     "6206404510689007446",
    "\u26a0":     "6206174450765796040",
    "\u2714":     "6206479140040743133",
}
for _k, _v in _EXTRA.items():
    PREMIUM_EMOJI_MAP.setdefault(_k, _v)
    PREMIUM_EMOJI_MAP.setdefault(_k + "\ufe0f", _v)
    PREMIUM_EMOJI_MAP.setdefault(_k.replace("\ufe0f", ""), _v)

_EMOJI_RE = re.compile(
    "|".join(re.escape(k) for k in sorted(PREMIUM_EMOJI_MAP, key=len, reverse=True))
)


def _wrap_emoji_segment(seg: str) -> str:
    return _EMOJI_RE.sub(
        lambda m: f'<tg-emoji emoji-id="{PREMIUM_EMOJI_MAP[m.group(0)]}">{m.group(0)}</tg-emoji>',
        seg,
    )


def premiumize_html(text: str) -> str:
    if not text:
        return text
    parts = re.split(r"(<tg-emoji[^>]*>.*?</tg-emoji>|<[^>]+>)", text)
    out = []
    in_code = 0
    for p in parts:
        if p.startswith("<tg-emoji") or p.startswith("<"):
            tag = p.lower()
            if tag.startswith(("<code", "<pre")):
                in_code += 1
            elif tag.startswith(("</code", "</pre")):
                in_code = max(0, in_code - 1)
            out.append(p)
        elif in_code:
            out.append(p)
        else:
            out.append(_wrap_emoji_segment(p))
    return "".join(out)


# ══════════════════════════════════════════════════════════════
#  TEXT STYLE ENGINE
# ══════════════════════════════════════════════════════════════

_SMALL_CAPS = dict(zip(
    "abcdefghijklmnopqrstuvwxyz",
    ["\u1d00","\u0299","\u1d04","\u1d05","\u1d07","\ua730","\u0262","\u029c","\u026a",
     "\u1d0a","\u1d0b","\u029f","\u1d0d","\u0274","\u1d0f","\u1d29","q","\u0280",
     "\ua731","\u1d1b","\u1d1c","\u1d20","\u1d21","x","\u028f","\u1d22"],
))
_UNSTYLE = {v: k for k, v in _SMALL_CAPS.items() if v != k}

_SKIP_RE  = re.compile(r"(<[^>]+>|&[a-zA-Z#0-9]+;|https?://\S+|@[A-Za-z0-9_]+|/[a-z_]+)")
_WORD_RE  = re.compile(r"[A-Za-z]+")


def _style_word(m: re.Match) -> str:
    w = m.group(0)
    out, first = [], True
    for ch in w:
        if first and ch.isalpha():
            out.append(ch.upper()); first = False
        else:
            out.append(_SMALL_CAPS.get(ch, ch))
    return "".join(out)


def stylize_text(text: str) -> str:
    if not text:
        return text
    parts = _SKIP_RE.split(text)
    out, in_code = [], False
    for part in parts:
        if not part:
            continue
        if part.startswith("<"):
            tag = part.lower()
            if tag.startswith(("<code", "<pre")):
                in_code = True
            elif tag.startswith(("</code", "</pre")):
                in_code = False
            out.append(part)
        elif _SKIP_RE.fullmatch(part):
            out.append(part)
        elif in_code:
            out.append(part)
        else:
            out.append(_WORD_RE.sub(_style_word, part))
    return "".join(out)


def unstyle_text(text: str) -> str:
    if not text:
        return text
    return "".join(_UNSTYLE.get(ch, ch) for ch in text)


def beautify(text: str, parse_mode=None):
    if not text:
        return text, parse_mode
    if parse_mode is None:
        text = html.escape(text)
        parse_mode = ParseMode.HTML
    elif str(parse_mode).lower() not in ("html", "parsemode.html"):
        return stylize_text(text), parse_mode
    styled = premiumize_html(stylize_text(text))
    if not styled.lstrip().startswith("<blockquote"):
        styled = f"<blockquote>{styled}</blockquote>"
    return styled, parse_mode


# ── Bot message hooks (message body only — NOT buttons) ──────
def _install_message_hooks() -> None:
    from telegram import Bot

    def _patch_text(name: str, field: str) -> None:
        original = getattr(Bot, name, None)
        if original is None or getattr(original, "_px_patched", False):
            return

        async def wrapper(self, *args, __orig=original, __field=field, **kwargs):
            if __field in kwargs and isinstance(kwargs[__field], str):
                new_text, pm = beautify(kwargs[__field], kwargs.get("parse_mode"))
                kwargs[__field] = new_text
                kwargs["parse_mode"] = pm
            return await __orig(self, *args, **kwargs)

        wrapper._px_patched = True
        setattr(Bot, name, wrapper)

    for _m in ("send_message", "edit_message_text"):
        _patch_text(_m, "text")
    for _m in ("send_photo","send_document","send_video","send_audio","send_voice",
               "send_animation","send_video_note","edit_message_caption"):
        _patch_text(_m, "caption")


_install_message_hooks()


# ══════════════════════════════════════════════════════════════
#  SAFE BUTTON ENGINE  (v3.1 fix)
# ══════════════════════════════════════════════════════════════

_IKB_SIG = _inspect_ptb.signature(InlineKeyboardButton.__init__).parameters
_KB_SIG  = _inspect_ptb.signature(KeyboardButton.__init__).parameters

_IKB_SUPPORTS_STYLE = "style" in _IKB_SIG
_IKB_SUPPORTS_ICON  = "icon_custom_emoji_id" in _IKB_SIG
_KB_SUPPORTS_STYLE  = "style" in _KB_SIG
_KB_SUPPORTS_ICON   = "icon_custom_emoji_id" in _KB_SIG

_VALID_STYLES = {"primary", "success", "danger"}


def _put_style(kwargs: dict, style: str, supported: bool) -> None:
    if style not in _VALID_STYLES:
        style = "primary"
    if supported:
        kwargs["style"] = style
    else:
        ak = dict(kwargs.get("api_kwargs") or {})
        ak.setdefault("style", style)
        kwargs["api_kwargs"] = ak


def _put_icon(kwargs: dict, icon_id: str | None, supported: bool) -> None:
    if not icon_id or not PREMIUM_EMOJI_BUTTONS:
        return
    if supported:
        kwargs["icon_custom_emoji_id"] = icon_id
    else:
        ak = dict(kwargs.get("api_kwargs") or {})
        ak.setdefault("icon_custom_emoji_id", icon_id)
        kwargs["api_kwargs"] = ak


def _ikb(text: str, *, style: str = "primary",
         icon_custom_emoji_id: str | None = None, **kwargs) -> InlineKeyboardButton:
    """Inline button. Text is stylized (safe — callback_data carries routing)."""
    _put_style(kwargs, style, _IKB_SUPPORTS_STYLE)
    _put_icon(kwargs, icon_custom_emoji_id, _IKB_SUPPORTS_ICON)
    return InlineKeyboardButton(stylize_text(text), **kwargs)


def _kb(text: str, *, style: str = "primary",
        icon_custom_emoji_id: str | None = None, **kwargs) -> KeyboardButton:
    """Reply keyboard button.

    ⚠️ Label is NEVER stylized. Telegram echoes the visible label back as
    message.text when tapped — if we change it, handle_text() routes dict
    stops matching and the button goes dead.
    """
    _put_style(kwargs, style, _KB_SUPPORTS_STYLE)
    _put_icon(kwargs, icon_custom_emoji_id, _KB_SUPPORTS_ICON)
    return KeyboardButton(text, **kwargs)


# ── Hash-based callback tags (kills 64-byte overflow) ────────
_tag_index: dict[str, str] = {}


def _tag_key(name: str) -> str:
    key = hashlib.md5(name.encode("utf-8")).hexdigest()[:12]
    _tag_index[key] = name
    return key


def _resolve_tag(key: str) -> str | None:
    if key in _tag_index:
        return _tag_index[key]
    # After restart the reverse map is empty — rebuild on miss.
    for name in DATABASES:
        if _tag_key(name) == key:
            return name
    return None


# ══════════════════════════════════════════════════════════════
#  RICH MESSAGE SYSTEM
# ══════════════════════════════════════════════════════════════

def _rich_media_binding(file_id: str, media_type: str):
    mt = (media_type or "").strip().lower()
    if mt in {"gif", "mp4_animation"}:
        mt = "animation"
    if mt == "photo":
        return (
            "tg://photo?id=hero_media",
            {"id": "hero_media", "media": {"type": "photo", "media": file_id}},
        )
    if mt in {"video", "animation"}:
        return (
            "tg://video?id=hero_media",
            {"id": "hero_media", "media": {"type": mt, "media": file_id}},
        )
    return None, None


def _rich_slideshow_binding(slides: list[dict]):
    if not slides:
        return "", []
    figures, media = [], []
    for i, slide in enumerate(slides):
        mt = (slide.get("type") or "photo").strip().lower()
        if mt in {"gif", "mp4_animation"}:
            mt = "animation"
        sid = f"slide{i}"
        tag = "video" if mt in {"video", "animation"} else "img"
        ref = "video" if tag == "video" else "photo"
        figures.append(f'<figure><{tag} src="tg://{ref}?id={sid}"/></figure>')
        media.append({"id": sid, "media": {"type": mt, "media": slide["file_id"]}})
    return "<tg-slideshow>" + "".join(figures) + "</tg-slideshow>", media


async def _send_rich_message(bot, chat_id, rich_message: dict, reply_markup=None):
    post = getattr(bot, "_post", None)
    if post is None:
        raise RuntimeError("No request layer")
    payload = {"chat_id": chat_id, "rich_message": rich_message}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup.to_dict()
    result = await post("sendRichMessage", data=payload)
    if isinstance(result, dict) and result.get("ok") is False:
        raise TelegramError(result.get("description", "Rich Message rejected"))
    return result


async def send_rich_or_fallback(
    bot, chat_id, rich_html: str, fallback_html: str,
    reply_markup=None, media_file_id="", media_type="",
    slides: list[dict] | None = None,
):
    rich_payload = {"html": premiumize_html(rich_html)}
    mt = (media_type or "").strip().lower()

    if slides:
        ss_html, ss_media = _rich_slideshow_binding(slides)
        rich_payload["html"] = ss_html + rich_payload["html"]
        rich_payload["media"] = ss_media
    elif media_file_id:
        ref, binding = _rich_media_binding(media_file_id, media_type)
        if ref and binding:
            hero = (
                f'<figure><img src="{ref}"/></figure>' if mt == "photo"
                else f'<figure><video src="{ref}"></video></figure>'
            )
            rich_payload["html"] = hero + rich_payload["html"]
            rich_payload["media"] = [binding]

    if RICH_MESSAGES_ENABLED:
        try:
            return await _send_rich_message(bot, chat_id, rich_payload, reply_markup)
        except (TelegramError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
            log.warning("Rich Message unavailable, using fallback: %s", exc)

    if slides:
        items = []
        for s in slides[:10]:
            smt = (s.get("type") or "photo").lower()
            if smt in {"video", "animation", "gif", "mp4_animation"}:
                items.append(InputMediaVideo(s["file_id"]))
            else:
                items.append(InputMediaPhoto(s["file_id"]))
        try:
            await bot.send_media_group(chat_id, items)
        except TelegramError:
            pass
        return await bot.send_message(chat_id, fallback_html, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    if media_file_id:
        if mt in {"gif", "mp4_animation", "animation"}:
            return await bot.send_animation(chat_id, media_file_id, caption=fallback_html, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        if mt == "video":
            return await bot.send_video(chat_id, media_file_id, caption=fallback_html, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        if mt == "photo":
            return await bot.send_photo(chat_id, media_file_id, caption=fallback_html, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    return await bot.send_message(chat_id, fallback_html, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


# ══════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════

DIVIDER      = "───────────────────────"
DIVIDER_THIN = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"


def ui_box(*lines: str) -> str:
    body = "\n".join(l for l in lines if l)
    return f"<blockquote>{body}</blockquote>" if body else ""


def ui_kv(icon: str, label: str, value: str) -> str:
    return f"{icon} <b>{label}:</b> {value}"


def ui_screen(icon: str, title: str, *blocks: str, subtitle: str = "", footer: str = "") -> str:
    header = (
        f"<blockquote>{DIVIDER}\n"
        f"{icon} <b>{title.upper()}</b>\n"
        f"{DIVIDER}</blockquote>"
    )
    sub = f"\n<i>{subtitle}</i>" if subtitle else ""
    body = "\n\n".join(b for b in blocks if b)
    foot = f"\n\n<blockquote><i>{footer}</i></blockquote>" if footer else ""
    return f"{header}{sub}\n\n{body}{foot}"


def ui_status(label: str, active: bool) -> str:
    dot = "🟢" if active else "🔴"
    state = "On" if active else "Off"
    return f"{dot} <b>{label}:</b> {state}"


def back_row(cb: str = "home", label: str = "⬅ Back") -> list:
    return [_ikb(label, callback_data=cb, style="primary")]


def kb_grid(buttons: list, cols: int = 2) -> list[list]:
    rows = []
    for i in range(0, len(buttons), cols):
        rows.append(buttons[i:i+cols])
    return rows


def pager_row(prefix: str, page: int, total_pages: int) -> list | None:
    if total_pages <= 1:
        return None
    btns = []
    if page > 0:
        btns.append(_ikb("⬅ Prev", callback_data=f"{prefix}{page-1}", style="primary"))
    btns.append(_ikb(f"📄 {page+1}/{total_pages}", callback_data="noop", style="primary"))
    if page < total_pages - 1:
        btns.append(_ikb("Next ➡", callback_data=f"{prefix}{page+1}", style="primary"))
    return btns if btns else None


# ══════════════════════════════════════════════════════════════
#  SQLITE DATABASE LAYER
# ══════════════════════════════════════════════════════════════

_db_path = SQLITE_DB_PATH
_db_conn_local: sqlite3.Connection | None = None
_db_lock = asyncio.Lock()


def _get_sync_conn() -> sqlite3.Connection:
    global _db_conn_local
    if _db_conn_local is None:
        _db_conn_local = sqlite3.connect(_db_path, check_same_thread=False)
        _db_conn_local.row_factory = sqlite3.Row
        _db_conn_local.execute("PRAGMA journal_mode=WAL")
        _db_conn_local.execute("PRAGMA synchronous=NORMAL")
    return _db_conn_local


@asynccontextmanager
async def db():
    async with _db_lock:
        conn = _get_sync_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


async def init_db() -> None:
    async with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS allowed_users (
            user_id INTEGER PRIMARY KEY, granted_by INTEGER, granted_at TEXT);
        CREATE TABLE IF NOT EXISTS all_users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            join_date TEXT, last_seen TEXT, referrals TEXT DEFAULT '[]');
        CREATE TABLE IF NOT EXISTS user_hub (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            phone TEXT NOT NULL, otp TEXT, db_name TEXT, db_url TEXT, timestamp TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_user_hub_user ON user_hub(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_hub_phone ON user_hub(phone);
        CREATE TABLE IF NOT EXISTS firebase_health (
            db_name TEXT PRIMARY KEY, db_url TEXT, status TEXT DEFAULT 'unknown',
            last_check TEXT, fail_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            filename TEXT NOT NULL, size_bytes INTEGER, target_chat INTEGER);
        CREATE TABLE IF NOT EXISTS monitor_subscriptions (
            user_id INTEGER PRIMARY KEY, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS welcome_config (
            id INTEGER PRIMARY KEY CHECK (id = 1), text TEXT, media_file_id TEXT,
            media_type TEXT, updated_at TEXT);
        INSERT OR IGNORE INTO welcome_config (id) VALUES (1);
        CREATE TABLE IF NOT EXISTS cloned_panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, source_name TEXT,
            db_url TEXT NOT NULL, created_at TEXT, notes TEXT);
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            action TEXT, detail TEXT, timestamp TEXT);
        CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id);
        """)
    log.info("SQLite database initialized: %s", _db_path)


# ── Settings helpers ─────────────────────────────────────────
_settings_cache: dict[str, str] = {}
_settings_lock = asyncio.Lock()

DEFAULT_SETTINGS = {
    "grant_access_required": "1",
    "referral_enabled":      "1",
    "required_referrals":    "2",
    "force_join_enabled":    "0",
    "auto_db_enabled":       "0",
    "auto_db_interval":      "3600",
    "auto_db_group":         "",
    "poll_interval":         "15",
    "monitor_enabled":       "0",
    "admin_only_tags":       "[]",
    "force_join_channels":   "[]",
    "bot_brand_name":        BOT_BRAND_NAME,
    "owner_display":         OWNER_DISPLAY,
    "owner_contact":         OWNER_CONTACT,
}


async def get_setting(key: str, default: str = "") -> str:
    async with _settings_lock:
        if key in _settings_cache:
            v = _settings_cache[key]
            return v if v not in (None, "") else default
    async with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        v = row["value"] if row else None
    async with _settings_lock:
        _settings_cache[key] = v or default
    return v if v not in (None, "") else default


async def set_setting(key: str, value: str) -> None:
    async with db() as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
    async with _settings_lock:
        _settings_cache[key] = value


async def get_setting_bool(key: str, default: bool = False) -> bool:
    v = await get_setting(key, "1" if default else "0")
    return v == "1"


async def get_setting_int(key: str, default: int = 0) -> int:
    v = await get_setting(key, str(default))
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


async def get_setting_json(key: str, default=None):
    v = await get_setting(key, "")
    if not v:
        return default
    try:
        return json.loads(v)
    except Exception:
        return default


async def _init_default_settings() -> None:
    for k, v in DEFAULT_SETTINGS.items():
        async with db() as conn:
            conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))


# ── Global in-memory state ──────────────────────────────────
DATABASES: dict[str, str] = dict(DEFAULT_DATABASES)
seen_ids: set[str] = set()
first_run: bool = True
_http_session: aiohttp.ClientSession | None = None
_main_app: Application | None = None
_fb_health: dict[str, dict] = {}
allowed_users: set[int] = set()
ADMIN_IDS: set[int] = {OWNER_ID}
pending_action: dict[int, dict] = {}
user_cooldowns: dict[int, float] = {}
user_focus: dict[int, str] = {}
user_page: dict[int, int] = {}


# ══════════════════════════════════════════════════════════════
#  ACCESS CONTROL
# ══════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def has_access(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    if not await get_setting_bool("grant_access_required", True):
        return True
    if user_id in allowed_users:
        return True
    if await get_setting_bool("referral_enabled", True):
        req = await get_setting_int("required_referrals", 2)
        count = await referral_count(user_id)
        if count >= req:
            return True
    return False


async def referral_count(user_id: int) -> int:
    async with db() as conn:
        row = conn.execute("SELECT referrals FROM all_users WHERE user_id=?", (user_id,)).fetchone()
    if not row or not row["referrals"]:
        return 0
    try:
        refs = json.loads(row["referrals"])
        return len(set(str(x) for x in refs))
    except Exception:
        return 0


async def grant_access(user_id: int, granted_by: int = OWNER_ID) -> None:
    allowed_users.add(user_id)
    async with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO allowed_users(user_id,granted_by,granted_at) VALUES(?,?,?)",
            (user_id, granted_by, datetime.utcnow().isoformat()),
        )


async def revoke_access(user_id: int) -> None:
    allowed_users.discard(user_id)
    async with db() as conn:
        conn.execute("DELETE FROM allowed_users WHERE user_id=?", (user_id,))


async def ensure_user(user_id: int, username: str | None, first_name: str | None) -> bool:
    now = datetime.utcnow().isoformat()
    async with db() as conn:
        exists = conn.execute("SELECT 1 FROM all_users WHERE user_id=?", (user_id,)).fetchone()
        if exists:
            conn.execute(
                "UPDATE all_users SET username=?,first_name=?,last_seen=? WHERE user_id=?",
                (username, first_name, now, user_id),
            )
            return False
        conn.execute(
            "INSERT INTO all_users(user_id,username,first_name,join_date,last_seen) VALUES(?,?,?,?,?)",
            (user_id, username, first_name, now, now),
        )
    return True


async def load_allowed_users() -> None:
    async with db() as conn:
        rows = conn.execute("SELECT user_id FROM allowed_users").fetchall()
    allowed_users.update(r["user_id"] for r in rows)


# ══════════════════════════════════════════════════════════════
#  USER HUB
# ══════════════════════════════════════════════════════════════

async def log_number_used(user_id: int, phone: str, otp: str | None,
                          db_name: str, db_url: str) -> None:
    async with db() as conn:
        conn.execute(
            "INSERT INTO user_hub(user_id,phone,otp,db_name,db_url,timestamp) VALUES(?,?,?,?,?,?)",
            (user_id, phone, otp, db_name, db_url, datetime.utcnow().isoformat()),
        )


async def get_user_hub(user_id: int, page: int = 0, per_page: int = 10) -> tuple[list, int]:
    offset = page * per_page
    async with db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM user_hub WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT phone,otp,db_name,timestamp FROM user_hub WHERE user_id=? "
            "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (user_id, per_page, offset),
        ).fetchall()
    return [dict(r) for r in rows], total


async def get_user_hub_stats(user_id: int) -> dict:
    async with db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM user_hub WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        unique_phones = conn.execute(
            "SELECT COUNT(DISTINCT phone) FROM user_hub WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        last_row = conn.execute(
            "SELECT timestamp FROM user_hub WHERE user_id=? ORDER BY timestamp DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        last_active = last_row[0] if last_row else None
    return {"total": total, "unique_phones": unique_phones, "last_active": last_active}


# ══════════════════════════════════════════════════════════════
#  FIREBASE HEALTH
# ══════════════════════════════════════════════════════════════

async def _ping_firebase(url: str, session: aiohttp.ClientSession) -> bool:
    try:
        test_url = url.rstrip("/") + "/.json?shallow=true&timeout=5s"
        async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            return resp.status in (200, 404)
    except Exception:
        return False


async def run_firebase_health_check(session: aiohttp.ClientSession) -> dict[str, str]:
    results: dict[str, str] = {}

    async def _check(name: str, url: str) -> None:
        alive = await _ping_firebase(url, session)
        status = "alive" if alive else "dead"
        results[name] = status
        _fb_health[name] = {"status": status, "last_check": time.time(), "url": url}
        async with db() as conn:
            existing = conn.execute(
                "SELECT fail_count FROM firebase_health WHERE db_name=?", (name,)
            ).fetchone()
            fail_count = (existing["fail_count"] or 0) if existing else 0
            fail_count = 0 if alive else fail_count + 1
            conn.execute(
                """INSERT INTO firebase_health(db_name,db_url,status,last_check,fail_count)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(db_name) DO UPDATE SET
                   db_url=excluded.db_url, status=excluded.status,
                   last_check=excluded.last_check, fail_count=excluded.fail_count""",
                (name, url, status, datetime.utcnow().isoformat(), fail_count),
            )

    tasks = [_check(name, url) for name, url in DATABASES.items()]
    await asyncio.gather(*tasks, return_exceptions=True)
    return results


def get_db_status_icon(name: str) -> str:
    h = _fb_health.get(name, {})
    status = h.get("status", "unknown")
    if status == "alive":
        return "🟢"
    if status == "dead":
        return "🔴"
    return "⚪"


async def remove_dead_databases() -> int:
    dead = [name for name, h in _fb_health.items() if h.get("status") == "dead"]
    for name in dead:
        DATABASES.pop(name, None)
    return len(dead)


# ══════════════════════════════════════════════════════════════
#  CLONE MANAGER
# ══════════════════════════════════════════════════════════════

async def clone_database(source_name: str, new_name: str, notes: str = "") -> bool:
    url = DATABASES.get(source_name)
    if not url:
        return False
    DATABASES[new_name] = url
    async with db() as conn:
        conn.execute(
            "INSERT INTO cloned_panels(name,source_name,db_url,created_at,notes) VALUES(?,?,?,?,?)",
            (new_name, source_name, url, datetime.utcnow().isoformat(), notes),
        )
    return True


async def get_cloned_panels() -> list[dict]:
    async with db() as conn:
        rows = conn.execute("SELECT * FROM cloned_panels ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
#  WELCOME CONFIG
# ══════════════════════════════════════════════════════════════

async def get_welcome_config() -> dict:
    async with db() as conn:
        row = conn.execute("SELECT * FROM welcome_config WHERE id=1").fetchone()
    if row:
        return dict(row)
    return {"text": None, "media_file_id": None, "media_type": None}


async def set_welcome_config(text: str | None = None,
                             media_file_id: str | None = None,
                             media_type: str | None = None) -> None:
    now = datetime.utcnow().isoformat()
    async with db() as conn:
        conn.execute(
            """UPDATE welcome_config SET text=COALESCE(?,text),
               media_file_id=COALESCE(?,media_file_id),
               media_type=COALESCE(?,media_type),
               updated_at=? WHERE id=1""",
            (text, media_file_id, media_type, now),
        )


async def clear_welcome_media() -> None:
    async with db() as conn:
        conn.execute(
            "UPDATE welcome_config SET media_file_id=NULL,media_type=NULL WHERE id=1"
        )


# ══════════════════════════════════════════════════════════════
#  BACKUP MANAGER
# ══════════════════════════════════════════════════════════════

def _build_snapshot() -> bytes:
    snapshot = {
        "version": BOT_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "databases": DATABASES,
        "allowed_users": list(allowed_users),
        "firebase_health": _fb_health,
    }
    return json.dumps(snapshot, ensure_ascii=False, indent=2).encode()


def _build_snapshot_gzip() -> bytes:
    return gzip.compress(_build_snapshot())


async def send_backup(bot, target_chat: int, compressed: bool = True) -> bool:
    try:
        data = _build_snapshot_gzip() if compressed else _build_snapshot()
        ext = "json.gz" if compressed else "json"
        fname = f"shownxpanel_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        await bot.send_document(
            chat_id=target_chat,
            document=io.BytesIO(data),
            filename=fname,
            caption=(
                f"🗄 <b>SHOWN X PANEL BACKUP</b>\n"
                f"📅 {datetime.now().strftime('%d %b %Y %H:%M:%S')}\n"
                f"💾 Size: {len(data)/1024:.1f} KB\n"
                f"🗜 Compressed: {'Yes' if compressed else 'No'}"
            ),
            parse_mode=ParseMode.HTML,
        )
        async with db() as conn:
            conn.execute(
                "INSERT INTO backup_history(timestamp,filename,size_bytes,target_chat) VALUES(?,?,?,?)",
                (datetime.utcnow().isoformat(), fname, len(data), target_chat),
            )
        return True
    except Exception as e:
        log.error("Backup send failed: %s", e)
        return False


async def get_backup_history(limit: int = 10) -> list[dict]:
    async with db() as conn:
        rows = conn.execute(
            "SELECT * FROM backup_history ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════
#  LIVE MONITOR
# ══════════════════════════════════════════════════════════════

_monitor_subs: set[int] = set()


async def load_monitor_subs() -> None:
    async with db() as conn:
        rows = conn.execute("SELECT user_id FROM monitor_subscriptions WHERE active=1").fetchall()
    _monitor_subs.update(r["user_id"] for r in rows)


async def toggle_monitor(user_id: int) -> bool:
    async with db() as conn:
        row = conn.execute(
            "SELECT active FROM monitor_subscriptions WHERE user_id=?", (user_id,)
        ).fetchone()
        if row:
            new_state = 0 if row["active"] else 1
            conn.execute(
                "UPDATE monitor_subscriptions SET active=? WHERE user_id=?",
                (new_state, user_id),
            )
        else:
            new_state = 1
            conn.execute(
                "INSERT INTO monitor_subscriptions(user_id,active) VALUES(?,1)", (user_id,)
            )
    if new_state:
        _monitor_subs.add(user_id)
    else:
        _monitor_subs.discard(user_id)
    return bool(new_state)


async def broadcast_otp_alert(bot, phone: str, otp: str, db_name: str) -> None:
    if not _monitor_subs:
        return
    text = (
        f"📡 <b>LIVE OTP ALERT</b>\n\n"
        f"📱 <b>Phone:</b> <code>{html.escape(phone)}</code>\n"
        f"🔑 <b>OTP:</b> <code>{html.escape(otp)}</code>\n"
        f"🗄 <b>DB:</b> {html.escape(db_name)}\n"
        f"🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}"
    )
    for uid in list(_monitor_subs):
        try:
            await bot.send_message(uid, text, parse_mode=ParseMode.HTML)
        except (Forbidden, TelegramError):
            _monitor_subs.discard(uid)


# ══════════════════════════════════════════════════════════════
#  ACTIVITY LOG
# ══════════════════════════════════════════════════════════════

async def log_activity(user_id: int, action: str, detail: str = "") -> None:
    async with db() as conn:
        conn.execute(
            "INSERT INTO activity_log(user_id,action,detail,timestamp) VALUES(?,?,?,?)",
            (user_id, action, detail, datetime.utcnow().isoformat()),
        )


# ══════════════════════════════════════════════════════════════
#  FORMAT HELPERS
# ══════════════════════════════════════════════════════════════

def fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M")
    except Exception:
        return iso or "—"


def fmt_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def html_escape(text: str) -> str:
    return html.escape(str(text))


def _tlog(msg: str) -> None:
    log.info(msg)


# ══════════════════════════════════════════════════════════════
#  HTTP SESSION
# ══════════════════════════════════════════════════════════════

async def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session


# ══════════════════════════════════════════════════════════════
#  FIREBASE FETCH
# ══════════════════════════════════════════════════════════════

async def fetch_firebase_sms(url: str, session: aiohttp.ClientSession) -> list[dict]:
    try:
        endpoints = [
            url.rstrip("/") + "/sms/.json",
            url.rstrip("/") + "/SMS/.json",
            url.rstrip("/") + "/messages/.json",
            url.rstrip("/") + "/otp/.json",
        ]
        for endpoint in endpoints:
            try:
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if data and isinstance(data, dict):
                            entries = []
                            for key, val in data.items():
                                if isinstance(val, dict):
                                    entries.append({**val, "_key": key})
                                elif isinstance(val, str):
                                    entries.append({"message": val, "_key": key})
                            if entries:
                                return entries
            except Exception:
                continue
    except Exception as e:
        log.debug("Firebase fetch error for %s: %s", url, e)
    return []


def extract_otp_from_entry(entry: dict) -> tuple[str, str]:
    phone = (
        entry.get("phone") or entry.get("mobile") or
        entry.get("number") or entry.get("to") or
        entry.get("Phone") or ""
    )
    message = (
        entry.get("message") or entry.get("body") or
        entry.get("text") or entry.get("sms") or
        entry.get("Message") or ""
    )
    otp = ""
    if message:
        m = re.search(r"\b(\d{4,8})\b", str(message))
        if m:
            otp = m.group(1)
    return str(phone).strip(), str(otp).strip()


# ══════════════════════════════════════════════════════════════
#  MIGRATION FROM OLD JSON
# ══════════════════════════════════════════════════════════════

async def migrate_from_json(json_path: str = "bot_database.json") -> None:
    if not Path(json_path).exists():
        return
    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        for uid in data.get("allowed_users", []):
            try:
                await grant_access(int(uid))
            except Exception:
                pass

        for name, url in data.get("databases", {}).items():
            if name not in DATABASES:
                DATABASES[name] = url

        for key in ("auto_db_enabled", "auto_db_interval", "auto_db_group",
                    "grant_access_required", "referral_enabled", "required_referrals"):
            if key in data:
                await set_setting(key, str(data[key]))

        log.info("Migrated from %s to SQLite", json_path)
        Path(json_path).rename(json_path + ".migrated")
    except Exception as e:
        log.warning("JSON migration failed: %s", e)


# ══════════════════════════════════════════════════════════════
#  REPLY + INLINE KEYBOARDS  (colored + safe labels)
# ══════════════════════════════════════════════════════════════

def main_menu_keyboard(admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [_kb("📡 Panel",  style="primary"), _kb("📊 Status", style="primary")],
        [_kb("👤 My Hub", style="success"), _kb("❓ Help",   style="primary")],
    ]
    if admin:
        rows.append([_kb("👑 Admin Panel", style="danger")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [_kb("🗄 DB Manager",    style="primary"), _kb("🔥 Firebase Health", style="success")],
        [_kb("📡 Live Monitor",  style="success"), _kb("💾 Backup",          style="primary")],
        [_kb("🧬 Clone Manager", style="primary"), _kb("🎨 Customize",       style="primary")],
        [_kb("👥 Users",         style="primary"), _kb("📊 Stats",           style="success")],
        [_kb("⚙ Settings",      style="primary"), _kb("⬅ Back",            style="danger")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def db_panel_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    items = list(DATABASES.items())
    per_page = 8
    start = page * per_page
    page_items = items[start:start + per_page]
    total_pages = max(1, (len(items) + per_page - 1) // per_page)

    rows = []
    for name, _url in page_items:
        status_icon = get_db_status_icon(name)
        key = _tag_key(name)
        rows.append([_ikb(f"{status_icon} {name}",
                          callback_data=f"db:view:{key}",
                          style="primary")])

    nav = []
    if page > 0:
        nav.append(_ikb("⬅", callback_data=f"db:page:{page-1}", style="primary"))
    nav.append(_ikb(f"{page+1}/{total_pages}", callback_data="noop", style="primary"))
    if page < total_pages - 1:
        nav.append(_ikb("➡", callback_data=f"db:page:{page+1}", style="primary"))
    if nav:
        rows.append(nav)

    rows.append([
        _ikb("🔥 Health Check", callback_data="db:health",      style="success"),
        _ikb("🗑 Remove Dead",  callback_data="db:remove_dead", style="danger"),
    ])
    rows.append([_ikb("➕ Add DB", callback_data="db:add", style="success")])
    rows.append(back_row("admin:home"))
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════════════════════
#  WELCOME TEXT
# ══════════════════════════════════════════════════════════════

async def build_welcome_text(user) -> str:
    quote = random.choice(PANEL_QUOTES)
    wc = await get_welcome_config()
    custom_text = wc.get("text") or ""
    brand = await get_setting("bot_brand_name", BOT_BRAND_NAME)
    owner = await get_setting("owner_contact", OWNER_CONTACT)
    mention = user.mention_html() if hasattr(user, "mention_html") else html_escape(str(user))

    base = (
        f"<blockquote>{DIVIDER}\n"
        f"⚡ <b>{html_escape(brand)}</b>\n"
        f"{DIVIDER}</blockquote>\n\n"
        f"👋 <b>Hey</b> {mention}!\n\n"
        f"<blockquote>{DIVIDER_THIN}\n"
        f"💬 <i>{html_escape(quote)}</i>\n"
        f"{DIVIDER_THIN}</blockquote>\n\n"
    )
    if custom_text:
        base += f"<blockquote>{html_escape(custom_text)}</blockquote>\n\n"

    base += (
        f"<blockquote>{DIVIDER}\n"
        f"👑 <b>Owner:</b> {html_escape(owner)}\n"
        f"🤖 <b>Version:</b> {BOT_VERSION}\n"
        f"{DIVIDER}</blockquote>"
    )
    return base


# ══════════════════════════════════════════════════════════════
#  POLL LOOP
# ══════════════════════════════════════════════════════════════

async def poll_all_databases(bot) -> None:
    global first_run
    session = await get_http_session()

    async def _poll_one(name: str, url: str) -> None:
        try:
            entries = await fetch_firebase_sms(url, session)
            for entry in entries:
                uid = entry.get("_key", "")
                if not uid or uid in seen_ids:
                    continue
                if len(seen_ids) >= MAX_SEEN_IDS:
                    seen_ids.clear()
                seen_ids.add(uid)

                if first_run:
                    continue

                phone, otp = extract_otp_from_entry(entry)
                if not phone and not otp:
                    continue

                raw_msg = entry.get("message") or entry.get("body") or entry.get("text") or ""

                alert = (
                    f"<blockquote>{'─'*22}\n"
                    f"📡 <b>NEW OTP RECEIVED</b>\n"
                    f"{'─'*22}</blockquote>\n\n"
                    f"<blockquote>"
                    f"🗄 <b>DB:</b> {html_escape(name)}\n"
                    f"📱 <b>Phone:</b> <code>{html_escape(phone)}</code>\n"
                    f"🔑 <b>OTP:</b> <code>{html_escape(otp)}</code>\n"
                    f"💬 <b>Msg:</b> <code>{html_escape(str(raw_msg)[:200])}</code>\n"
                    f"🕐 <b>Time:</b> {datetime.now().strftime('%d %b %Y %H:%M:%S')}"
                    f"</blockquote>"
                )

                copy_btn = None
                if otp and _PTB_COPY_TEXT_BUTTON:
                    try:
                        copy_btn = InlineKeyboardMarkup([[_PTB_COPY_TEXT_BUTTON(otp)]])
                    except Exception:
                        copy_btn = None

                targets = set(allowed_users) | ADMIN_IDS
                for uid2 in targets:
                    try:
                        await bot.send_message(uid2, alert, parse_mode=ParseMode.HTML,
                                               reply_markup=copy_btn)
                    except (Forbidden, BadRequest):
                        pass
                    except RetryAfter as e:
                        await asyncio.sleep(e.retry_after)

                if otp:
                    await broadcast_otp_alert(bot, phone, otp, name)

                for uid2 in targets:
                    try:
                        await log_number_used(uid2, phone, otp, name, url)
                    except Exception:
                        pass

                await log_activity(0, "otp_received", f"{name}|{phone}|{otp}")

        except Exception as e:
            log.debug("Poll error for %s: %s", name, e)

    tasks = [_poll_one(name, url) for name, url in list(DATABASES.items())]
    await asyncio.gather(*tasks, return_exceptions=True)
    first_run = False


async def poll_loop(bot) -> None:
    log.info("OTP poll loop started")
    while True:
        try:
            interval = await get_setting_int("poll_interval", POLL_INTERVAL)
            await poll_all_databases(bot)
            await asyncio.sleep(max(5, interval))
        except asyncio.CancelledError:
            log.info("Poll loop cancelled")
            break
        except Exception as e:
            log.error("Poll loop error: %s", e)
            await asyncio.sleep(10)


# ══════════════════════════════════════════════════════════════
#  AUTO BACKUP LOOP
# ══════════════════════════════════════════════════════════════

async def auto_backup_loop(bot) -> None:
    log.info("Auto backup loop started")
    while True:
        try:
            enabled = await get_setting_bool("auto_db_enabled", False)
            if enabled:
                interval = await get_setting_int("auto_db_interval", 3600)
                target_raw = await get_setting("auto_db_group", "")
                if target_raw:
                    try:
                        target = int(target_raw)
                        await send_backup(bot, target)
                        log.info("Auto backup sent to %s", target)
                    except Exception as e:
                        log.error("Auto backup failed: %s", e)
                await asyncio.sleep(max(300, interval))
            else:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Auto backup loop error: %s", e)
            await asyncio.sleep(60)


# ══════════════════════════════════════════════════════════════
#  FIREBASE HEALTH LOOP
# ══════════════════════════════════════════════════════════════

async def firebase_health_loop(bot) -> None:
    log.info("Firebase health loop started")
    while True:
        try:
            session = await get_http_session()
            results = await run_firebase_health_check(session)
            dead = sum(1 for s in results.values() if s == "dead")
            alive = sum(1 for s in results.values() if s == "alive")
            log.info("Firebase health: %d alive, %d dead", alive, dead)
            await asyncio.sleep(FB_HEALTH_INTERVAL)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Health loop error: %s", e)
            await asyncio.sleep(60)


# ══════════════════════════════════════════════════════════════
#  GUARD
# ══════════════════════════════════════════════════════════════

async def guard_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False
    await ensure_user(user.id, user.username, user.first_name)
    if await has_access(user.id):
        return True
    ref_link = f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=ref_{user.id}"
    req = await get_setting_int("required_referrals", 2)
    count = await referral_count(user.id)
    text = (
        f"<blockquote>{'─'*22}\n"
        f"🔒 <b>ACCESS REQUIRED</b>\n"
        f"{'─'*22}</blockquote>\n\n"
        f"<blockquote>"
        f"⚡ You need access to use this panel.\n\n"
        f"📨 <b>Option 1:</b> Contact owner {html_escape(await get_setting('owner_contact', OWNER_CONTACT))}\n\n"
        f"🔗 <b>Option 2:</b> Refer {req} friends:\n"
        f"<code>{html_escape(ref_link)}</code>\n\n"
        f"👥 Your referrals: <b>{count}/{req}</b>"
        f"</blockquote>"
    )
    if update.callback_query:
        try:
            await update.callback_query.answer("🔒 Access required", show_alert=True)
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return False


# ══════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    await ensure_user(user.id, user.username, user.first_name)
    await log_activity(user.id, "start", "")

    args = context.args or []
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0][4:])
            if referrer_id != user.id:
                async with db() as conn:
                    row = conn.execute(
                        "SELECT referrals FROM all_users WHERE user_id=?", (referrer_id,)
                    ).fetchone()
                    refs = json.loads(row["referrals"] or "[]") if row else []
                    if str(user.id) not in [str(x) for x in refs]:
                        refs.append(user.id)
                        conn.execute(
                            "UPDATE all_users SET referrals=? WHERE user_id=?",
                            (json.dumps(refs), referrer_id),
                        )
        except Exception:
            pass

    welcome_text = await build_welcome_text(user)
    wc = await get_welcome_config()
    media_id = wc.get("media_file_id")
    media_type = wc.get("media_type") or "photo"
    admin = is_admin(user.id)
    kb = main_menu_keyboard(admin)

    if media_id:
        try:
            if media_type == "photo":
                await context.bot.send_photo(user.id, media_id, caption=welcome_text,
                                             parse_mode=ParseMode.HTML, reply_markup=kb)
            elif media_type == "video":
                await context.bot.send_video(user.id, media_id, caption=welcome_text,
                                             parse_mode=ParseMode.HTML, reply_markup=kb)
            elif media_type in ("animation", "gif"):
                await context.bot.send_animation(user.id, media_id, caption=welcome_text,
                                                 parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML,
                                                reply_markup=kb)
            return
        except Exception:
            pass

    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  /panel
# ══════════════════════════════════════════════════════════════

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_access(update, context):
        return
    total_dbs = len(DATABASES)
    alive_count = sum(1 for h in _fb_health.values() if h.get("status") == "alive")
    brand = await get_setting("bot_brand_name", BOT_BRAND_NAME)

    text = ui_screen(
        "📡", f"{brand} — OTP PANEL",
        ui_box(
            ui_kv("🗄", "Total DBs", str(total_dbs)),
            ui_kv("🟢", "Alive", str(alive_count)),
            ui_kv("🔴", "Dead", str(total_dbs - alive_count)),
            ui_kv("👥", "Users", str(len(allowed_users))),
        ),
        ui_box(f"💬 <i>{random.choice(PANEL_QUOTES)}</i>"),
        subtitle="Select a database to view OTPs",
        footer=f"Last updated: {datetime.now().strftime('%H:%M:%S')}",
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=db_panel_keyboard(0))


# ══════════════════════════════════════════════════════════════
#  /status
# ══════════════════════════════════════════════════════════════

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_access(update, context):
        return
    total = len(DATABASES)
    alive = sum(1 for h in _fb_health.values() if h.get("status") == "alive")
    dead  = sum(1 for h in _fb_health.values() if h.get("status") == "dead")
    unk   = total - alive - dead
    poll_int = await get_setting_int("poll_interval", POLL_INTERVAL)
    monitor_on = update.effective_user.id in _monitor_subs

    text = ui_screen(
        "📊", "SYSTEM STATUS",
        ui_box(
            ui_kv("🗄", "Total DBs", str(total)),
            ui_kv("🟢", "Alive", str(alive)),
            ui_kv("🔴", "Dead", str(dead)),
            ui_kv("⚪", "Unchecked", str(unk)),
        ),
        ui_box(
            ui_kv("⏱", "Poll Interval", f"{poll_int}s"),
            ui_kv("👁", "Seen IDs", str(len(seen_ids))),
            ui_status("Live Monitor", monitor_on),
        ),
        footer=f"🕐 {datetime.now().strftime('%d %b %Y %H:%M:%S')}",
    )
    kb = InlineKeyboardMarkup([
        [_ikb("🔥 Run Health Check", callback_data="db:health", style="success")],
        [_ikb("📡 Toggle Monitor", callback_data="monitor:toggle", style="primary")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  /hub
# ══════════════════════════════════════════════════════════════

async def cmd_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_access(update, context):
        return
    await _show_user_hub(update, context, update.effective_user.id, 0, edit=False)


async def _show_user_hub(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         user_id: int, page: int, edit: bool = False) -> None:
    stats = await get_user_hub_stats(user_id)
    rows, total = await get_user_hub(user_id, page, 8)
    total_pages = max(1, (total + 7) // 8)

    if rows:
        lines = []
        for r in rows:
            ts = r.get("timestamp", "")[:16].replace("T", " ")
            phone = r.get("phone") or "—"
            otp = r.get("otp") or "—"
            db_name = r.get("db_name") or "—"
            lines.append(
                f"📱 <code>{html_escape(phone)}</code> | "
                f"🔑 <code>{html_escape(otp)}</code>\n"
                f"   🗄 {html_escape(db_name[:20])} · 🕐 {ts}"
            )
        entries_block = ui_box("\n\n".join(lines))
    else:
        entries_block = ui_box("📭 No number history yet.")

    text = ui_screen(
        "👤", "USER HUB",
        ui_box(
            ui_kv("📊", "Total Hits", str(stats["total"])),
            ui_kv("📱", "Unique Numbers", str(stats["unique_phones"])),
            ui_kv("🕐", "Last Active", fmt_date(stats["last_active"])),
        ),
        entries_block,
        subtitle=f"Page {page+1} of {total_pages}",
    )

    nav = []
    if page > 0:
        nav.append(_ikb("⬅ Prev", callback_data=f"hub:page:{page-1}", style="primary"))
    nav.append(_ikb(f"{page+1}/{total_pages}", callback_data="noop", style="primary"))
    if page < total_pages - 1:
        nav.append(_ikb("Next ➡", callback_data=f"hub:page:{page+1}", style="primary"))

    rows_kb = []
    if nav:
        rows_kb.append(nav)
    rows_kb.append([_ikb("🗑 Clear My History", callback_data="hub:clear", style="danger")])
    rows_kb.append(back_row("home"))
    kb = InlineKeyboardMarkup(rows_kb)

    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except BadRequest:
            pass
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  /admin
# ══════════════════════════════════════════════════════════════

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return
    brand = await get_setting("bot_brand_name", BOT_BRAND_NAME)
    total_dbs = len(DATABASES)
    alive = sum(1 for h in _fb_health.values() if h.get("status") == "alive")
    async with db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM all_users").fetchone()[0]
    text = ui_screen(
        "👑", f"{brand} — ADMIN PANEL",
        ui_box(
            ui_kv("🗄", "Total DBs", str(total_dbs)),
            ui_kv("🟢", "Alive", str(alive)),
            ui_kv("👥", "Total Users", str(total_users)),
            ui_kv("🔑", "Allowed", str(len(allowed_users))),
        ),
        footer="Select a section below",
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML,
                                    reply_markup=admin_menu_keyboard())


# ══════════════════════════════════════════════════════════════
#  TEXT HANDLER
# ══════════════════════════════════════════════════════════════

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    user = update.effective_user

    pa = pending_action.get(user.id)
    if pa:
        await _handle_pending(update, context, pa, text)
        return

    routes = {
        "📡 Panel":          cmd_panel,
        "📊 Status":         cmd_status,
        "👤 My Hub":         cmd_hub,
        "❓ Help":           cmd_help,
        "👑 Admin Panel":    cmd_admin,
        "🗄 DB Manager":     _admin_db_manager,
        "🔥 Firebase Health":_admin_health_text,
        "📡 Live Monitor":   _admin_monitor_text,
        "💾 Backup":         _admin_backup_text,
        "🧬 Clone Manager":  _admin_clone_text,
        "🎨 Customize":      _admin_customize_text,
        "👥 Users":          _admin_users_text,
        "📊 Stats":          _admin_stats_text,
        "⚙ Settings":       _admin_settings_text,
        "⬅ Back":           _go_home,
    }

    # Direct hit
    fn = routes.get(text)

    # Fallback for old keyboards that may have styled labels (post-restart)
    if fn is None:
        norm = re.sub(r"\s+", " ", unstyle_text(text or "")).strip()
        fn = routes.get(norm)

    if fn:
        await fn(update, context)
        return

    # Unknown input — send a clean fallback, never silent
    admin = is_admin(user.id)
    await update.message.reply_text(
        f"❓ <b>Ye option samajh nahi aaya.</b>\n\n"
        f"<i>Menu dobara kholne ke liye /start bhejein.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(admin),
    )


# ══════════════════════════════════════════════════════════════
#  PENDING ACTION HANDLER
# ══════════════════════════════════════════════════════════════

async def _handle_pending(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          pa: dict, text: str) -> None:
    user = update.effective_user
    action = pa.get("action")

    if action == "add_db":
        parts = text.strip().split(None, 1)
        if len(parts) != 2 or not parts[1].startswith("http"):
            await update.message.reply_text(
                "❌ Format: <b>DB_NAME https://your-firebase-url</b>",
                parse_mode=ParseMode.HTML,
            )
            return
        name, url = parts
        DATABASES[name] = url
        pending_action.pop(user.id, None)
        await update.message.reply_text(
            f"✅ <b>Added:</b> <code>{html_escape(name)}</code>",
            parse_mode=ParseMode.HTML,
        )

    elif action == "grant_user":
        try:
            uid = int(text.strip())
            await grant_access(uid, user.id)
            pending_action.pop(user.id, None)
            await update.message.reply_text(
                f"✅ Access granted to <code>{uid}</code>",
                parse_mode=ParseMode.HTML,
            )
        except ValueError:
            await update.message.reply_text("❌ Send a valid user ID (numbers only)")

    elif action == "revoke_user":
        try:
            uid = int(text.strip())
            await revoke_access(uid)
            pending_action.pop(user.id, None)
            await update.message.reply_text(
                f"🚫 Access revoked for <code>{uid}</code>",
                parse_mode=ParseMode.HTML,
            )
        except ValueError:
            await update.message.reply_text("❌ Send a valid user ID")

    elif action == "set_welcome_text":
        await set_welcome_config(text=text)
        pending_action.pop(user.id, None)
        await update.message.reply_text("✅ <b>Welcome text updated!</b>",
                                        parse_mode=ParseMode.HTML)

    elif action == "set_backup_target":
        try:
            chat_id = int(text.strip())
            await set_setting("auto_db_group", str(chat_id))
            pending_action.pop(user.id, None)
            await update.message.reply_text(
                f"✅ Backup target set to <code>{chat_id}</code>",
                parse_mode=ParseMode.HTML,
            )
        except ValueError:
            await update.message.reply_text("❌ Send a valid chat ID")

    elif action == "clone_db":
        parts = text.strip().split(None, 1)
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Format: <b>SOURCE_NAME NEW_NAME</b>",
                parse_mode=ParseMode.HTML,
            )
            return
        src, new = parts
        ok = await clone_database(src, new)
        pending_action.pop(user.id, None)
        if ok:
            await update.message.reply_text(
                f"✅ Cloned <code>{html_escape(src)}</code> → <code>{html_escape(new)}</code>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text(f"❌ Source <code>{html_escape(src)}</code> not found.")

    elif action == "set_poll_interval":
        try:
            val = max(5, int(text.strip()))
            await set_setting("poll_interval", str(val))
            pending_action.pop(user.id, None)
            await update.message.reply_text(f"✅ Poll interval set to <b>{val}s</b>",
                                            parse_mode=ParseMode.HTML)
        except ValueError:
            await update.message.reply_text("❌ Send a number (seconds)")

    elif action == "broadcast":
        pending_action.pop(user.id, None)
        async with db() as conn:
            rows = conn.execute("SELECT user_id FROM all_users").fetchall()
        targets = [r["user_id"] for r in rows]
        sent, failed = 0, 0
        for tid in targets:
            try:
                await context.bot.send_message(tid, text, parse_mode=ParseMode.HTML)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"📡 <b>Broadcast done</b>\n✅ Sent: <b>{sent}</b> | ❌ Failed: <b>{failed}</b>",
            parse_mode=ParseMode.HTML,
        )

    elif action == "set_refs_required":
        try:
            val = max(1, int(text.strip()))
            await set_setting("required_referrals", str(val))
            pending_action.pop(user.id, None)
            await update.message.reply_text(f"✅ Referrals required set to <b>{val}</b>",
                                            parse_mode=ParseMode.HTML)
        except ValueError:
            await update.message.reply_text("❌ Send a number (e.g. 2)")

    elif action == "set_brand":
        name = text.strip()[:50]
        await set_setting("bot_brand_name", name)
        pending_action.pop(user.id, None)
        await update.message.reply_text(f"✅ Brand name set to <b>{html_escape(name)}</b>",
                                        parse_mode=ParseMode.HTML)


# Photo/video handler for welcome media
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    pa = pending_action.get(user.id)
    if not pa or pa.get("action") != "set_welcome_media":
        return
    msg = update.message
    if msg.photo:
        fid, mt = msg.photo[-1].file_id, "photo"
    elif msg.video:
        fid, mt = msg.video.file_id, "video"
    elif msg.animation:
        fid, mt = msg.animation.file_id, "animation"
    else:
        return
    await set_welcome_config(media_file_id=fid, media_type=mt)
    pending_action.pop(user.id, None)
    await update.message.reply_text(
        f"✅ <b>Welcome media updated!</b> Type: <code>{mt}</code>",
        parse_mode=ParseMode.HTML,
    )


# ══════════════════════════════════════════════════════════════
#  ADMIN TEXT MENU HANDLERS
# ══════════════════════════════════════════════════════════════

async def _admin_db_manager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    text = ui_screen(
        "🗄", "DATABASE MANAGER",
        ui_box(
            ui_kv("📦", "Total DBs", str(len(DATABASES))),
            ui_kv("🟢", "Alive", str(sum(1 for h in _fb_health.values() if h.get("status") == "alive"))),
            ui_kv("🔴", "Dead", str(sum(1 for h in _fb_health.values() if h.get("status") == "dead"))),
        ),
        subtitle="Manage your Firebase databases",
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML,
                                    reply_markup=db_panel_keyboard(0))


async def _admin_health_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "⏳ <b>Running Firebase health check...</b>",
        parse_mode=ParseMode.HTML,
    )
    session = await get_http_session()
    results = await run_firebase_health_check(session)
    alive = sum(1 for s in results.values() if s == "alive")
    dead = sum(1 for s in results.values() if s == "dead")
    lines = []
    for name, status in results.items():
        icon = "🟢" if status == "alive" else "🔴"
        lines.append(f"{icon} {html_escape(name[:30])}")
    block = ui_box("\n".join(lines[:30]))
    if len(lines) > 30:
        block += f"\n<i>...and {len(lines)-30} more</i>"
    text = ui_screen(
        "🔥", "FIREBASE HEALTH REPORT",
        ui_box(
            ui_kv("🟢", "Alive", str(alive)),
            ui_kv("🔴", "Dead", str(dead)),
            ui_kv("📊", "Total", str(len(results))),
        ),
        block,
        footer=f"Checked: {datetime.now().strftime('%H:%M:%S')}",
    )
    kb = InlineKeyboardMarkup([
        [_ikb("🗑 Remove All Dead", callback_data="db:remove_dead", style="danger")],
        [_ikb("🔄 Recheck", callback_data="db:health", style="success")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _admin_monitor_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    user_id = update.effective_user.id
    is_on = user_id in _monitor_subs
    text = ui_screen(
        "📡", "LIVE MONITOR",
        ui_box(
            ui_status("Your Monitor", is_on),
            ui_kv("👥", "Subscribers", str(len(_monitor_subs))),
        ),
        subtitle="Get live OTP alerts as they arrive",
    )
    kb = InlineKeyboardMarkup([
        [_ikb("🔴 Turn Off" if is_on else "🟢 Turn On",
              callback_data="monitor:toggle",
              style="danger" if is_on else "success")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _admin_backup_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    history = await get_backup_history(5)
    auto_on = await get_setting_bool("auto_db_enabled", False)
    interval = await get_setting_int("auto_db_interval", 3600)
    target = await get_setting("auto_db_group", "")

    if history:
        lines = []
        for h in history:
            sz = fmt_size(h.get("size_bytes") or 0)
            ts = fmt_date(h.get("timestamp"))
            lines.append(f"📦 {ts} · {sz}")
        hist_block = ui_box("\n".join(lines))
    else:
        hist_block = ui_box("📭 No backups yet.")

    text = ui_screen(
        "💾", "BACKUP MANAGER",
        ui_box(
            ui_status("Auto Backup", auto_on),
            ui_kv("⏱", "Interval", f"{interval//3600}h {(interval%3600)//60}m"),
            ui_kv("📤", "Target Chat", target or "Not set"),
        ),
        hist_block,
        subtitle="Compressed gzip backups",
    )
    kb = InlineKeyboardMarkup([
        [_ikb("📤 Backup Now", callback_data="backup:now", style="success")],
        [
            _ikb("🔴 Disable" if auto_on else "🟢 Enable",
                 callback_data="backup:toggle_auto",
                 style="danger" if auto_on else "success"),
            _ikb("🎯 Set Target", callback_data="backup:set_target", style="primary"),
        ],
        [_ikb("📋 Full History", callback_data="backup:history", style="primary")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _admin_clone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    clones = await get_cloned_panels()
    if clones:
        lines = []
        for c in clones[:10]:
            lines.append(
                f"🧬 <b>{html_escape(c['name'])}</b>\n"
                f"   ← {html_escape(c.get('source_name') or '?')} · {fmt_date(c.get('created_at'))}"
            )
        clones_block = ui_box("\n\n".join(lines))
    else:
        clones_block = ui_box("📭 No clones yet.")

    text = ui_screen(
        "🧬", "CLONE MANAGER",
        ui_box(ui_kv("📦", "Total Clones", str(len(clones)))),
        clones_block,
        subtitle="Duplicate DB configs under new names",
    )
    kb = InlineKeyboardMarkup([
        [_ikb("➕ Clone a DB", callback_data="clone:start", style="success")],
        [_ikb("📋 All Clones", callback_data="clone:list:0", style="primary")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _admin_customize_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    wc = await get_welcome_config()
    has_media = bool(wc.get("media_file_id"))
    has_text = bool(wc.get("text"))
    brand = await get_setting("bot_brand_name", BOT_BRAND_NAME)
    owner_contact = await get_setting("owner_contact", OWNER_CONTACT)

    text = ui_screen(
        "🎨", "CUSTOMIZE STUDIO",
        ui_box(
            ui_kv("🏷", "Brand Name", html_escape(brand)),
            ui_kv("👑", "Owner Contact", html_escape(owner_contact)),
            ui_status("Welcome Text", has_text),
            ui_status("Welcome Media", has_media),
            ui_kv("🖼", "Media Type", html_escape(wc.get("media_type") or "—")),
        ),
        subtitle="Customize welcome screen & bot identity",
    )
    kb = InlineKeyboardMarkup([
        [_ikb("✏ Edit Welcome Text", callback_data="cust:edit_text", style="primary")],
        [_ikb("🖼 Set Welcome Media", callback_data="cust:edit_media", style="primary")],
        [_ikb("🗑 Clear Media", callback_data="cust:clear_media", style="danger")],
        [_ikb("👁 Preview Welcome", callback_data="cust:preview", style="success")],
        [_ikb("🏷 Change Brand Name", callback_data="cust:brand", style="primary")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _admin_users_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    async with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM all_users").fetchone()[0]
    text = ui_screen(
        "👥", "USER MANAGER",
        ui_box(
            ui_kv("👥", "Total Users", str(total)),
            ui_kv("🔑", "Allowed", str(len(allowed_users))),
        ),
    )
    kb = InlineKeyboardMarkup([
        [
            _ikb("✅ Grant Access", callback_data="user:grant", style="success"),
            _ikb("🚫 Revoke Access", callback_data="user:revoke", style="danger"),
        ],
        [_ikb("📋 Allowed List", callback_data="user:list:0", style="primary")],
        [_ikb("📡 Broadcast", callback_data="user:broadcast", style="primary")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _admin_stats_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    async with db() as conn:
        total_users  = conn.execute("SELECT COUNT(*) FROM all_users").fetchone()[0]
        total_otps   = conn.execute("SELECT COUNT(*) FROM user_hub").fetchone()[0]
        total_phones = conn.execute("SELECT COUNT(DISTINCT phone) FROM user_hub").fetchone()[0]
        backups      = conn.execute("SELECT COUNT(*) FROM backup_history").fetchone()[0]
        clones       = conn.execute("SELECT COUNT(*) FROM cloned_panels").fetchone()[0]
        today_otps   = conn.execute(
            "SELECT COUNT(*) FROM user_hub WHERE timestamp >= ?",
            (datetime.utcnow().strftime("%Y-%m-%d"),)
        ).fetchone()[0]

    text = ui_screen(
        "📊", "STATS DASHBOARD",
        ui_box(
            ui_kv("👥", "Total Users", str(total_users)),
            ui_kv("🔑", "Allowed", str(len(allowed_users))),
            ui_kv("🗄", "Total DBs", str(len(DATABASES))),
            ui_kv("🧬", "Clones", str(clones)),
        ),
        ui_box(
            ui_kv("📱", "Total OTPs", str(total_otps)),
            ui_kv("📅", "Today OTPs", str(today_otps)),
            ui_kv("📞", "Unique Phones", str(total_phones)),
            ui_kv("💾", "Backups Made", str(backups)),
        ),
        footer=f"🕐 {datetime.now().strftime('%d %b %Y %H:%M:%S')}",
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def _admin_settings_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    grant_req    = await get_setting_bool("grant_access_required", True)
    ref_en       = await get_setting_bool("referral_enabled", True)
    ref_req      = await get_setting_int("required_referrals", 2)
    poll_int     = await get_setting_int("poll_interval", POLL_INTERVAL)
    auto_bk      = await get_setting_bool("auto_db_enabled", False)

    text = ui_screen(
        "⚙", "SETTINGS",
        ui_box(
            ui_status("Access Control", grant_req),
            ui_status("Referral System", ref_en),
            ui_kv("👥", "Refs Required", str(ref_req)),
            ui_kv("⏱", "Poll Interval", f"{poll_int}s"),
            ui_status("Auto Backup", auto_bk),
        ),
    )
    kb = InlineKeyboardMarkup([
        [_ikb("🔴 Disable Access Control" if grant_req else "🟢 Enable Access Control",
              callback_data="settings:toggle_grant",
              style="danger" if grant_req else "success")],
        [_ikb("🔴 Disable Referrals" if ref_en else "🟢 Enable Referrals",
              callback_data="settings:toggle_referral",
              style="danger" if ref_en else "success")],
        [_ikb("⏱ Set Poll Interval", callback_data="settings:poll", style="primary")],
        [_ikb("🔢 Set Refs Required", callback_data="settings:refs", style="primary")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _go_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin = is_admin(update.effective_user.id)
    await update.message.reply_text("🏠 Main Menu", reply_markup=main_menu_keyboard(admin))


# ══════════════════════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════════════════════

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    brand = await get_setting("bot_brand_name", BOT_BRAND_NAME)
    text = ui_screen(
        "❓", f"{brand} — HELP",
        ui_box(
            "📡 <b>Panel</b> — Browse all DBs + live status icons",
            "📊 <b>Status</b> — System health overview",
            "👤 <b>My Hub</b> — Your full number history",
            "❓ <b>Help</b> — This screen",
        ),
        ui_box(
            "🗄 <b>DB Manager</b> — Add/remove/view DBs",
            "🔥 <b>Firebase Health</b> — Ping all DBs live",
            "📡 <b>Live Monitor</b> — Real-time OTP alerts",
            "💾 <b>Backup</b> — Manual/auto gzip backups",
            "🧬 <b>Clone Manager</b> — Duplicate DB configs",
            "🎨 <b>Customize</b> — Welcome text + media",
            "👥 <b>Users</b> — Grant/revoke access",
            "📊 <b>Stats</b> — Dashboard",
        ),
        subtitle="All commands available via reply keyboard",
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════
#  CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    user = q.from_user

    if data == "noop":
        return

    if data == "home":
        admin = is_admin(user.id)
        try:
            await q.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            user.id, "🏠 Main Menu",
            reply_markup=main_menu_keyboard(admin),
        )
        return

    if data == "admin:home":
        try:
            await q.message.delete()
        except Exception:
            pass
        brand = await get_setting("bot_brand_name", BOT_BRAND_NAME)
        await context.bot.send_message(
            user.id,
            ui_screen("👑", f"{brand} — ADMIN PANEL",
                      ui_box("Select a section below")),
            parse_mode=ParseMode.HTML,
            reply_markup=admin_menu_keyboard(),
        )
        return

    if data.startswith("db:page:"):
        if not is_admin(user.id):
            return
        page = int(data.split(":")[-1])
        try:
            await q.edit_message_reply_markup(reply_markup=db_panel_keyboard(page))
        except BadRequest:
            pass
        return

    if data.startswith("db:view:"):
        name = _resolve_tag(data[8:])
        if not name:
            await q.answer("DB not found — refresh karo", show_alert=True)
            return
        url = DATABASES.get(name, "")
        h = _fb_health.get(name, {})
        status = h.get("status", "unknown")
        last_check = fmt_date(
            datetime.fromtimestamp(h["last_check"]).isoformat()
            if "last_check" in h else None
        )
        icon = get_db_status_icon(name)
        key = _tag_key(name)
        text = ui_screen(
            icon, f"DB: {name}",
            ui_box(
                ui_kv("🔗", "URL", f"<code>{html_escape(url[:60])}</code>"),
                ui_kv("📊", "Status", status.upper()),
                ui_kv("🕐", "Last Check", last_check),
            ),
        )
        kb = InlineKeyboardMarkup([
            [_ikb("🔥 Ping", callback_data=f"db:ping:{key}", style="success")],
            [_ikb("🧬 Clone", callback_data=f"db:clone_this:{key}", style="primary")],
            [_ikb("🗑 Remove", callback_data=f"db:remove:{key}", style="danger")],
            back_row("admin:home"),
        ])
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except BadRequest:
            pass
        return

    if data.startswith("db:ping:"):
        name = _resolve_tag(data[8:])
        if not name:
            await q.answer("DB not found", show_alert=True)
            return
        url = DATABASES.get(name, "")
        if not url:
            await q.answer("DB has no URL", show_alert=True)
            return
        session = await get_http_session()
        alive = await _ping_firebase(url, session)
        status = "🟢 ALIVE" if alive else "🔴 DEAD"
        _fb_health[name] = {"status": "alive" if alive else "dead",
                            "last_check": time.time(), "url": url}
        await q.answer(f"{name}: {status}", show_alert=True)
        return

    if data.startswith("db:remove:"):
        if not is_admin(user.id):
            return
        name = _resolve_tag(data[10:])
        if not name:
            await q.answer("DB not found", show_alert=True)
            return
        DATABASES.pop(name, None)
        _fb_health.pop(name, None)
        await q.answer(f"✅ Removed {name}")
        try:
            await q.edit_message_reply_markup(reply_markup=db_panel_keyboard(0))
        except BadRequest:
            pass
        return

    if data == "db:health":
        if not is_admin(user.id):
            return
        await q.answer("⏳ Running health check...")
        session = await get_http_session()
        results = await run_firebase_health_check(session)
        alive = sum(1 for s in results.values() if s == "alive")
        dead = sum(1 for s in results.values() if s == "dead")
        await q.answer(f"✅ Done: {alive} alive, {dead} dead", show_alert=True)
        try:
            await q.edit_message_reply_markup(reply_markup=db_panel_keyboard(0))
        except BadRequest:
            pass
        return

    if data == "db:remove_dead":
        if not is_admin(user.id):
            return
        count = await remove_dead_databases()
        await q.answer(f"🗑 Removed {count} dead DBs", show_alert=True)
        try:
            await q.edit_message_reply_markup(reply_markup=db_panel_keyboard(0))
        except BadRequest:
            pass
        return

    if data == "db:add":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "add_db"}
        await context.bot.send_message(
            user.id,
            "📥 <b>Send DB info:</b>\n\n<code>DB_NAME https://your-firebase-url</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("db:clone_this:"):
        if not is_admin(user.id):
            return
        src = _resolve_tag(data[14:])
        if not src:
            await q.answer("DB not found", show_alert=True)
            return
        pending_action[user.id] = {"action": "clone_db"}
        await context.bot.send_message(
            user.id,
            f"🧬 <b>Clone:</b> <code>{html_escape(src)}</code>\n\n"
            f"Send: <code>{html_escape(src)} NEW_NAME</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "monitor:toggle":
        new_state = await toggle_monitor(user.id)
        status = "🟢 ON" if new_state else "🔴 OFF"
        await q.answer(f"Live Monitor: {status}", show_alert=True)
        return

    if data.startswith("hub:page:"):
        page = int(data.split(":")[-1])
        await _show_user_hub(update, context, user.id, page, edit=True)
        return

    if data == "hub:clear":
        async with db() as conn:
            conn.execute("DELETE FROM user_hub WHERE user_id=?", (user.id,))
        await q.answer("🗑 History cleared", show_alert=True)
        await _show_user_hub(update, context, user.id, 0, edit=True)
        return

    if data == "backup:now":
        if not is_admin(user.id):
            return
        await q.answer("⏳ Sending backup...")
        ok = await send_backup(context.bot, user.id)
        await q.answer("✅ Backup sent!" if ok else "❌ Backup failed", show_alert=True)
        return

    if data == "backup:toggle_auto":
        if not is_admin(user.id):
            return
        cur = await get_setting_bool("auto_db_enabled", False)
        await set_setting("auto_db_enabled", "0" if cur else "1")
        await q.answer(f"Auto backup: {'OFF' if cur else 'ON'}", show_alert=True)
        return

    if data == "backup:set_target":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_backup_target"}
        await context.bot.send_message(
            user.id,
            "📤 <b>Send target chat ID</b> (group/channel ID):",
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "backup:history":
        if not is_admin(user.id):
            return
        history = await get_backup_history(10)
        lines = []
        for h in history:
            sz = fmt_size(h.get("size_bytes") or 0)
            ts = fmt_date(h.get("timestamp"))
            fn = h.get("filename", "—")
            lines.append(f"📦 {ts}\n   {html_escape(fn)} · {sz}")
        block = ui_box("\n\n".join(lines) if lines else "📭 No backups yet.")
        text = ui_screen("💾", "BACKUP HISTORY", block)
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([back_row("admin:home")]))
        except BadRequest:
            pass
        return

    if data == "clone:start":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "clone_db"}
        await context.bot.send_message(
            user.id,
            "🧬 <b>Clone a DB</b>\n\nSend: <code>SOURCE_NAME NEW_NAME</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("clone:list:"):
        if not is_admin(user.id):
            return
        page = int(data.split(":")[-1])
        clones = await get_cloned_panels()
        per_page = 5
        start = page * per_page
        items = clones[start:start+per_page]
        total_pages = max(1, (len(clones) + per_page - 1) // per_page)
        lines = []
        for c in items:
            lines.append(
                f"🧬 <b>{html_escape(c['name'])}</b>\n"
                f"   ← {html_escape(c.get('source_name') or '?')}"
            )
        block = ui_box("\n\n".join(lines) if lines else "📭 None.")
        text = ui_screen("🧬", "CLONE LIST", block, subtitle=f"Page {page+1}/{total_pages}")
        nav = []
        if page > 0:
            nav.append(_ikb("⬅", callback_data=f"clone:list:{page-1}", style="primary"))
        if page < total_pages - 1:
            nav.append(_ikb("➡", callback_data=f"clone:list:{page+1}", style="primary"))
        rows_kb = [nav] if nav else []
        rows_kb.append(back_row("admin:home"))
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(rows_kb))
        except BadRequest:
            pass
        return

    if data == "cust:edit_text":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_welcome_text"}
        await context.bot.send_message(
            user.id, "✏ <b>Send new welcome text:</b>", parse_mode=ParseMode.HTML)
        return

    if data == "cust:edit_media":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_welcome_media"}
        await context.bot.send_message(
            user.id, "🖼 <b>Send photo, video, or GIF for welcome screen:</b>",
            parse_mode=ParseMode.HTML)
        return

    if data == "cust:clear_media":
        if not is_admin(user.id):
            return
        await clear_welcome_media()
        await q.answer("🗑 Media cleared", show_alert=True)
        return

    if data == "cust:preview":
        wc = await get_welcome_config()
        media_id = wc.get("media_file_id")
        media_type = wc.get("media_type") or "photo"
        text = await build_welcome_text(user)
        if media_id:
            try:
                if media_type == "photo":
                    await context.bot.send_photo(user.id, media_id, caption=text, parse_mode=ParseMode.HTML)
                elif media_type == "video":
                    await context.bot.send_video(user.id, media_id, caption=text, parse_mode=ParseMode.HTML)
                elif media_type in ("animation", "gif"):
                    await context.bot.send_animation(user.id, media_id, caption=text, parse_mode=ParseMode.HTML)
            except Exception:
                await context.bot.send_message(user.id, text, parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_message(user.id, text, parse_mode=ParseMode.HTML)
        await q.answer("👁 Preview sent")
        return

    if data == "cust:brand":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_brand"}
        await context.bot.send_message(
            user.id, "🏷 <b>Send new brand name:</b>", parse_mode=ParseMode.HTML)
        return

    if data == "user:grant":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "grant_user"}
        await context.bot.send_message(user.id, "📨 Send the User ID to grant access:")
        return

    if data == "user:revoke":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "revoke_user"}
        await context.bot.send_message(user.id, "🚫 Send the User ID to revoke access:")
        return

    if data == "user:broadcast":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "broadcast"}
        await context.bot.send_message(
            user.id,
            "📡 <b>Send broadcast message:</b>\n\n"
            "It will be sent to all users in the system.\n"
            "HTML formatting supported.",
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith("user:list:"):
        if not is_admin(user.id):
            return
        page = int(data.split(":")[-1])
        per_page = 10
        items = list(allowed_users)
        start = page * per_page
        chunk = items[start:start+per_page]
        total_pages = max(1, (len(items) + per_page - 1) // per_page)
        lines = [f"🔑 <code>{uid}</code>" for uid in chunk]
        block = ui_box("\n".join(lines) if lines else "📭 No allowed users.")
        text = ui_screen("👥", "ALLOWED USERS", block, subtitle=f"Page {page+1}/{total_pages}")
        nav = []
        if page > 0:
            nav.append(_ikb("⬅", callback_data=f"user:list:{page-1}", style="primary"))
        if page < total_pages - 1:
            nav.append(_ikb("➡", callback_data=f"user:list:{page+1}", style="primary"))
        rows_kb = [nav] if nav else []
        rows_kb.append(back_row("admin:home"))
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(rows_kb))
        except BadRequest:
            pass
        return

    if data == "settings:toggle_grant":
        if not is_admin(user.id):
            return
        cur = await get_setting_bool("grant_access_required", True)
        await set_setting("grant_access_required", "0" if cur else "1")
        await q.answer(f"Access control: {'OFF' if cur else 'ON'}", show_alert=True)
        return

    if data == "settings:toggle_referral":
        if not is_admin(user.id):
            return
        cur = await get_setting_bool("referral_enabled", True)
        await set_setting("referral_enabled", "0" if cur else "1")
        await q.answer(f"Referral system: {'OFF' if cur else 'ON'}", show_alert=True)
        return

    if data == "settings:poll":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_poll_interval"}
        await context.bot.send_message(user.id, "⏱ Send poll interval in seconds (min 5):")
        return

    if data == "settings:refs":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_refs_required"}
        await context.bot.send_message(user.id, "🔢 Send number of referrals required:")
        return


# ══════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════════════════════════

async def cmd_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /grant USER_ID")
        return
    try:
        uid = int(context.args[0])
        await grant_access(uid, update.effective_user.id)
        await update.message.reply_text(f"✅ Granted: <code>{uid}</code>",
                                        parse_mode=ParseMode.HTML)
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid user ID")


async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /revoke USER_ID")
        return
    try:
        uid = int(context.args[0])
        await revoke_access(uid)
        await update.message.reply_text(f"🚫 Revoked: <code>{uid}</code>",
                                        parse_mode=ParseMode.HTML)
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid user ID")


async def cmd_adddb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /adddb DB_NAME https://url")
        return
    name = context.args[0]
    url = context.args[1]
    DATABASES[name] = url
    await update.message.reply_text(f"✅ Added: <code>{html_escape(name)}</code>",
                                    parse_mode=ParseMode.HTML)


async def cmd_removedb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /removedb DB_NAME")
        return
    name = " ".join(context.args)
    if name in DATABASES:
        DATABASES.pop(name)
        await update.message.reply_text(f"🗑 Removed: <code>{html_escape(name)}</code>",
                                        parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ DB not found")


async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏳ Preparing backup...")
    ok = await send_backup(context.bot, update.effective_user.id)
    if not ok:
        await update.message.reply_text("❌ Backup failed")


async def cmd_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    new_state = await toggle_monitor(update.effective_user.id)
    status = "🟢 ON" if new_state else "🔴 OFF"
    await update.message.reply_text(f"📡 <b>Live Monitor: {status}</b>",
                                    parse_mode=ParseMode.HTML)


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏳ Checking all Firebase DBs...")
    session = await get_http_session()
    results = await run_firebase_health_check(session)
    alive = sum(1 for s in results.values() if s == "alive")
    dead = sum(1 for s in results.values() if s == "dead")
    await update.message.reply_text(
        f"✅ Health check done:\n🟢 Alive: <b>{alive}</b>\n🔴 Dead: <b>{dead}</b>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await _admin_stats_text(update, context)


# ══════════════════════════════════════════════════════════════
#  ERROR HANDLER
# ══════════════════════════════════════════════════════════════

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, (Conflict, asyncio.CancelledError)):
        return
    if isinstance(err, RetryAfter):
        await asyncio.sleep(err.retry_after)
        return
    if isinstance(err, (Forbidden, ChatMigrated)):
        return
    log.error("Update error: %s", traceback.format_exc())


# ══════════════════════════════════════════════════════════════
#  HEALTH SERVER
# ══════════════════════════════════════════════════════════════

async def health_server() -> None:
    from aiohttp import web

    async def health_check(request):
        return web.Response(
            text=json.dumps({
                "status": "ok",
                "version": BOT_VERSION,
                "dbs": len(DATABASES),
                "users": len(allowed_users),
            }),
            content_type="application/json",
        )

    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HEALTH_CHECK_PORT)
    await site.start()
    log.info("Health server on port %s", HEALTH_CHECK_PORT)


# ══════════════════════════════════════════════════════════════
#  POST INIT
# ══════════════════════════════════════════════════════════════

async def post_init(app: Application) -> None:
    await init_db()
    await _init_default_settings()
    await migrate_from_json()
    await load_allowed_users()
    await load_monitor_subs()

    app.create_task(poll_loop(app.bot), name="poll_loop")
    app.create_task(auto_backup_loop(app.bot), name="auto_backup_loop")
    app.create_task(firebase_health_loop(app.bot), name="firebase_health_loop")

    try:
        app.create_task(health_server(), name="health_server")
    except Exception as e:
        log.warning("Health server not started: %s", e)

    log.info(
        "SHOWN X PANEL %s started | DBs: %d | Allowed: %d",
        BOT_VERSION, len(DATABASES), len(allowed_users),
    )


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main() -> None:
    global _main_app

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )
    _main_app = app

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("panel",    cmd_panel))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("hub",      cmd_hub))
    app.add_handler(CommandHandler("admin",    cmd_admin))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("grant",    cmd_grant))
    app.add_handler(CommandHandler("revoke",   cmd_revoke))
    app.add_handler(CommandHandler("adddb",    cmd_adddb))
    app.add_handler(CommandHandler("removedb", cmd_removedb))
    app.add_handler(CommandHandler("backup",   cmd_backup))
    app.add_handler(CommandHandler("monitor",  cmd_monitor))
    app.add_handler(CommandHandler("health",   cmd_health))
    app.add_handler(CommandHandler("stats",    cmd_stats))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION,
        handle_media,
    ))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    log.info("Starting bot polling...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
