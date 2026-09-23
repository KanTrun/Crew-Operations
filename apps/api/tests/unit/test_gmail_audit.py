# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Audit: kiểm tra cascade delete và tính nhất quán của Gmail.

Các test ở đây là test CHẨN ĐOÁN — cố tình phơi bày lỗi để xác nhận trước khi sửa.
"""

from __future__ import annotations

from ca_api import persist


def _table_count(account_id: str, table: str) -> int:
    with persist._conn() as cx:
        row = cx.execute(
            f"SELECT COUNT(*) FROM {table} WHERE account_id=?", (account_id,)
        ).fetchone()
    return int(row[0])


def test_delete_account_cascades_all_child_rows() -> None:
    """Xoá tài khoản PHẢI dọn sạch token/mail/nhãn/bộ lọc — nếu không là rò rỉ dữ liệu."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="cascade@gmail.com"
    )
    aid = str(acc["id"])

    persist.gmail_token_save(
        aid,
        access_token="gia-tri-gia-a",
        refresh_token="gia-tri-gia-b",
        expires_at="2030-01-01T00:00:00Z",
        scope="scope",
        token_type="Bearer",
    )
    persist.gmail_message_upsert(
        aid,
        message_id="msg_1",
        thread_id="th_1",
        label_ids=["INBOX"],
        snippet="x",
        from_email="a@b.com",
        to_emails=["c@d.com"],
        cc_emails=[],
        subject="s",
        body_text="body",
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=False,
        is_starred=False,
        has_attachment=False,
    )
    persist.gmail_label_upsert(aid, label_id="Label_1", name="Nhãn")
    persist.gmail_filter_upsert(
        aid, filter_id="filter_1", criteria={"from": "a@b.com"}, action={}
    )
    persist.gmail_sync_state_upsert(aid, last_history_id="12345")

    assert _table_count(aid, "gmail_oauth_tokens") == 1
    assert _table_count(aid, "gmail_messages") == 1
    assert _table_count(aid, "gmail_labels") == 1
    assert _table_count(aid, "gmail_filters") == 1
    assert _table_count(aid, "gmail_sync_state") == 1

    assert persist.gmail_account_delete(aid) is True

    # ── ĐÂY LÀ ĐIỀU CẦN ĐÚNG ──
    leaks = {
        "gmail_oauth_tokens": _table_count(aid, "gmail_oauth_tokens"),
        "gmail_messages": _table_count(aid, "gmail_messages"),
        "gmail_labels": _table_count(aid, "gmail_labels"),
        "gmail_filters": _table_count(aid, "gmail_filters"),
        "gmail_sync_state": _table_count(aid, "gmail_sync_state"),
    }
    assert leaks == dict.fromkeys(leaks, 0), f"RÒ RỈ dữ liệu sau khi xoá: {leaks}"


def test_foreign_keys_pragma_enabled() -> None:
    """SQLite mặc định TẮT foreign keys — cascade vô hiệu nếu không bật."""
    with persist._conn() as cx:
        row = cx.execute("PRAGMA foreign_keys").fetchone()
    assert int(row[0]) == 1, "PRAGMA foreign_keys chưa bật ⇒ ON DELETE CASCADE vô hiệu"


def test_message_upsert_updates_existing_not_duplicate() -> None:
    """Đồng bộ lại cùng email không được tạo bản ghi trùng."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="upsert@gmail.com"
    )
    aid = str(acc["id"])
    payload = dict(
        message_id="msg_dup",
        thread_id="th_1",
        label_ids=["INBOX"],
        snippet="ban đầu",
        from_email="a@b.com",
        to_emails=["c@d.com"],
        cc_emails=[],
        subject="s",
        body_text="body",
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=False,
        is_starred=False,
        has_attachment=False,
    )
    persist.gmail_message_upsert(aid, **payload)
    persist.gmail_message_upsert(aid, **{**payload, "snippet": "cập nhật", "is_read": True})

    rows = persist.gmail_messages_list(aid, limit=50)
    assert len(rows) == 1, f"Bản ghi trùng: {len(rows)}"
    assert rows[0]["snippet"] == "cập nhật"
    assert rows[0]["is_read"] is True


def test_messages_are_scoped_per_account() -> None:
    """Email của tài khoản A không được lộ qua truy vấn của tài khoản B."""
    a = persist.gmail_account_create(store_id="quan_01", nv_id="nv_01", email="a@gmail.com")
    b = persist.gmail_account_create(store_id="quan_01", nv_id="nv_01", email="b@gmail.com")
    persist.gmail_message_upsert(
        str(a["id"]),
        message_id="msg_a",
        thread_id="th",
        label_ids=[],
        snippet="của A",
        from_email="x@y.com",
        to_emails=[],
        cc_emails=[],
        subject="s",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=True,
        is_starred=False,
        has_attachment=False,
    )
    assert persist.gmail_messages_list(str(b["id"])) == []


def test_sync_state_defaults_do_not_clobber_existing() -> None:
    """Gọi upsert chỉ với last_history_id không được xoá total_messages đã lưu."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="sync@gmail.com"
    )
    aid = str(acc["id"])
    persist.gmail_sync_state_upsert(aid, last_history_id="100", total_messages=42, unread_count=7)

    # Lần sync tăng dần sau đó chỉ cập nhật history id, không truyền số đếm.
    state = persist.gmail_sync_state_upsert(aid, last_history_id="200")

    assert state["last_history_id"] == "200"
    assert state["total_messages"] == 42, "total_messages bị ghi đè về 0"
    assert state["unread_count"] == 7, "unread_count bị ghi đè về 0"


def test_token_encrypted_at_rest() -> None:
    """Token phải nằm dạng mã hoá trong DB, không phải plaintext."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="enc@gmail.com"
    )
    aid = str(acc["id"])
    # Giá trị giả đặc trưng — KHÔNG phải bí mật; dùng để chứng minh không lưu plaintext.
    # Đặt đúng quy ước allowlist của scripts/scan_secrets_before_commit.py.
    gia_tri_kiem_thu = "KHONG_PHAI_BI_MAT_KIEM_THU_DAC_TRUNG"
    persist.gmail_token_save(
        aid,
        access_token=gia_tri_kiem_thu,
        refresh_token=None,
        expires_at="2030-01-01T00:00:00Z",
    )
    with persist._conn() as cx:
        raw = cx.execute(
            "SELECT access_token_enc FROM gmail_oauth_tokens WHERE account_id=?", (aid,)
        ).fetchone()
    assert gia_tri_kiem_thu not in str(raw[0]), "Token lưu plaintext trong DB"
    assert persist.gmail_token_get(aid)["access_token"] == gia_tri_kiem_thu


def test_search_query_escapes_like_wildcards() -> None:
    """`%` trong ô tìm kiếm không được hoạt động như ký tự đại diện.

    Nếu không escape, gõ `%` sẽ khớp MỌI email — người dùng tưởng lọc được
    nhưng thực chất thấy hết, và khó phát hiện vì trông như "có kết quả".
    """
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="like@gmail.com"
    )
    aid = str(acc["id"])
    for idx, subject in enumerate(["Báo giá cà phê", "Đơn hàng 100% cacao"]):
        persist.gmail_message_upsert(
            aid,
            message_id=f"m{idx}",
            thread_id="t",
            label_ids=["INBOX"],
            snippet=subject,
            from_email="a@b.com",
            to_emails=[],
            cc_emails=[],
            subject=subject,
            body_text=None,
            body_html=None,
            internal_date=f"2026-01-0{idx + 1}T00:00:00Z",
            is_read=True,
            is_starred=False,
            has_attachment=False,
        )

    # Tìm đúng chuỗi có '%' ⇒ chỉ 1 kết quả, không phải cả 2.
    rows = persist.gmail_messages_list(aid, query="100%")
    assert len(rows) == 1, f"Wildcard rò rỉ: {[r['subject'] for r in rows]}"
    assert rows[0]["subject"] == "Đơn hàng 100% cacao"

    # Chuỗi tìm không tồn tại ⇒ rỗng, không khớp bừa.
    assert persist.gmail_messages_list(aid, query="%%%") == []


def test_search_is_case_insensitive_for_ascii() -> None:
    """Tìm kiếm không phân biệt hoa thường với ký tự ASCII."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="case@gmail.com"
    )
    aid = str(acc["id"])
    persist.gmail_message_upsert(
        aid,
        message_id="mcase",
        thread_id="t",
        label_ids=[],
        snippet="Invoice from supplier",
        from_email="supplier@example.com",
        to_emails=[],
        cc_emails=[],
        subject="Invoice from Supplier",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=True,
        is_starred=False,
        has_attachment=False,
    )
    assert len(persist.gmail_messages_list(aid, query="invoice")) == 1
    assert len(persist.gmail_messages_list(aid, query="SUPPLIER")) == 1


def test_label_filter_escapes_wildcards() -> None:
    """Nhãn chứa `%`/`_` không được khớp nhầm nhãn khác."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="labelesc@gmail.com"
    )
    aid = str(acc["id"])
    persist.gmail_message_upsert(
        aid,
        message_id="mlabel",
        thread_id="t",
        label_ids=["Label_100%"],
        snippet="x",
        from_email="a@b.com",
        to_emails=[],
        cc_emails=[],
        subject="s",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=True,
        is_starred=False,
        has_attachment=False,
    )
    # Nhãn này không tồn tại ⇒ không được khớp nhờ '%' là wildcard.
    assert persist.gmail_messages_list(aid, label_ids=["Label_1___"]) == []
    assert len(persist.gmail_messages_list(aid, label_ids=["Label_100%"])) == 1


def test_label_filters_are_json_roundtrip() -> None:
    """Nhãn/bộ lọc lưu JSON phải đọc lại đúng kiểu, không trả str."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="json@gmail.com"
    )
    aid = str(acc["id"])
    persist.gmail_message_upsert(
        aid,
        message_id="m",
        thread_id="t",
        label_ids=["INBOX", "UNREAD"],
        snippet="x",
        from_email="a@b.com",
        to_emails=["c@d.com"],
        cc_emails=["e@f.com"],
        subject="s",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=False,
        is_starred=True,
        has_attachment=True,
    )
    row = persist.gmail_messages_list(aid)[0]
    assert row["label_ids"] == ["INBOX", "UNREAD"]
    assert row["to_emails"] == ["c@d.com"]
    assert row["cc_emails"] == ["e@f.com"]
    assert row["has_attachment"] is True
    assert row["is_starred"] is True


def test_message_get_returns_correct_fields() -> None:
    """`gmail_message_get` phải trả đúng từng cột (từng có bug lệch index: subject lấy nhầm cc)."""
    acc = persist.gmail_account_create(
        store_id="quan_01", nv_id="nv_01", email="field@gmail.com"
    )
    aid = str(acc["id"])
    persist.gmail_message_upsert(
        aid,
        message_id="m_fields",
        thread_id="thread_abc",
        label_ids=["INBOX", "STARRED"],
        snippet="đoạn trích",
        from_email="nguoigui@example.com",
        to_emails=["nguoinhan@example.com"],
        cc_emails=["cc@example.com"],
        subject="Chủ đề thật",
        body_text="thân thư",
        body_html="<p>thân thư</p>",
        internal_date="2026-05-05T10:00:00Z",
        is_read=True,
        is_starred=True,
        has_attachment=False,
    )
    row = persist.gmail_message_get(aid, "m_fields")
    assert row is not None
    assert row["subject"] == "Chủ đề thật"
    assert row["snippet"] == "đoạn trích"
    assert row["from_email"] == "nguoigui@example.com"
    assert row["to_emails"] == ["nguoinhan@example.com"]
    assert row["cc_emails"] == ["cc@example.com"]
    assert row["thread_id"] == "thread_abc"
    assert row["body_text"] == "thân thư"
    assert row["body_html"] == "<p>thân thư</p>"
    assert row["internal_date"] == "2026-05-05T10:00:00Z"
    assert row["is_read"] is True
    assert row["is_starred"] is True

    # Truy vấn list phải cho cùng giá trị (hai hàm từng lệch nhau).
    listed = persist.gmail_messages_list(aid)[0]
    for key in ("subject", "snippet", "from_email", "to_emails", "cc_emails", "thread_id"):
        assert listed[key] == row[key], f"list và get lệch ở {key}"


# ── Bảo mật: cách ly dữ liệu giữa nhân viên (IDOR) ───────────────────────

def test_gmail_message_get_returns_own_record_only() -> None:
    """`gmail_message_get` phải khoá theo account_id — không đọc chéo tài khoản."""
    a = persist.gmail_account_create(store_id="quan_01", nv_id="nv_01", email="idor_a@gmail.com")
    b = persist.gmail_account_create(store_id="quan_01", nv_id="nv_03", email="idor_b@gmail.com")
    persist.gmail_message_upsert(
        str(b["id"]),
        message_id="msg_cua_B",
        thread_id="th",
        label_ids=[],
        snippet="bí mật của B",
        from_email="x@y.com",
        to_emails=[],
        cc_emails=[],
        subject="s",
        body_text=None,
        body_html=None,
        internal_date="2026-01-01T00:00:00Z",
        is_read=True,
        is_starred=False,
        has_attachment=False,
    )
    # A hỏi id của message thuộc B ⇒ phải None
    assert persist.gmail_message_get(str(a["id"]), "msg_cua_B") is None

    # A đánh dấu đọc message của B ⇒ phải False
    assert persist.gmail_message_mark_read(str(a["id"]), "msg_cua_B") is False
    assert persist.gmail_message_star(str(a["id"]), "msg_cua_B") is False

    # Nhãn/filter của B không lộ qua truy vấn của A
    persist.gmail_label_upsert(str(b["id"]), label_id="L_B", name="Nhãn B")
    assert persist.gmail_labels_list(str(a["id"])) == []

