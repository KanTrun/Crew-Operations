"""So sánh hai bản phân công để CHỨNG MINH điều gì đã thay đổi.

Vì sao cần một mô-đun riêng thay vì tính tại chỗ ở từng router: cùng một câu hỏi
"ai bị đổi ca, ai vào thay" được hỏi ở BA nguồn khác nhau — xếp lịch tự động,
xác nhận thời khoá biểu bận, và chợ đổi ca. Ba nơi tự tính thì con số sẽ lệch
nhau (bài học từ hai route lifecycle đã lệch ma trận chuyển tiếp), và người dùng
đọc ba màn hình thấy ba câu trả lời khác nhau thì không tin cái nào.

Mô-đun này THUẦN: không đọc DB, không gọi mạng, không phụ thuộc FastAPI. Đầu vào
là hai dict phân công + bảng tra ca/nhân viên. Nhờ vậy nó test được không cần
dựng server, và luật "phân loại thay đổi" nằm ở đúng một chỗ để đọc.

QUY ƯỚC SỐ/KHỐI LƯỢNG (theo `ca_contracts/loss.py`): danh sách RỖNG nghĩa là
"không có thay đổi", không phải "chưa có dữ liệu". Trường hợp thiếu dữ liệu đầu
vào thể hiện bằng `None`, và khi đó `khong_so_sanh_duoc = True` — KHÔNG được suy
diễn thành "không có gì đổi".
"""

from __future__ import annotations

from typing import Any


def _as_id_list(value: Any) -> list[str]:
    """Chuẩn hoá một giá trị phân công về danh sách id, giữ THỨ TỰ xuất hiện."""
    if not isinstance(value, (list, tuple)):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in value:
        nv_id = str(item).strip()
        if nv_id and nv_id not in seen:
            seen.add(nv_id)
            out.append(nv_id)
    return out


def _ten(nv_id: str, nhan_vien: dict[str, Any] | None) -> str:
    """Tên hiển thị của nhân viên; thiếu dữ liệu thì trả chính id, KHÔNG bịa."""
    if not nhan_vien:
        return nv_id
    entry = nhan_vien.get(nv_id)
    if isinstance(entry, dict):
        for key in ("ten", "ho_ten", "name"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    elif isinstance(entry, str) and entry.strip():
        return entry.strip()
    return nv_id


def _ca_info(ca_id: str, ca_meta: dict[str, Any] | None) -> dict[str, Any]:
    """Mô tả ngắn một ca để UI hiện được mà không cần tra thêm."""
    meta = (ca_meta or {}).get(ca_id)
    if not isinstance(meta, dict):
        return {"ca_id": ca_id, "thu": "", "khung": "", "gio": "", "vi_tri": ""}
    bat_dau = str(meta.get("bat_dau") or "").strip()
    ket_thuc = str(meta.get("ket_thuc") or "").strip()
    return {
        "ca_id": ca_id,
        "thu": str(meta.get("thu") or "").strip(),
        "khung": str(meta.get("khung") or "").strip(),
        "gio": f"{bat_dau}-{ket_thuc}" if bat_dau and ket_thuc else "",
        "vi_tri": str(meta.get("vi_tri") or "").strip(),
    }


def so_sanh_phan_cong(
    truoc: dict[str, list[str]] | None,
    sau: dict[str, list[str]] | None,
    *,
    ca_meta: dict[str, Any] | None = None,
    nhan_vien: dict[str, Any] | None = None,
    gioi_han: int = 200,
) -> dict[str, Any]:
    """So sánh hai bản phân công và trả về thay đổi theo TỪNG CA.

    Đầu vào `truoc`/`sau` là `{ca_id: [nv_id, ...]}`. `ca_meta` cho tên/giờ ca,
    `nhan_vien` cho tên người. Cả hai đều tuỳ chọn — thiếu thì trả id thô.

    Trả về:
      - `them`:   [(ca_id, nv_id)] người mới được xếp vào ca (trước không có).
      - `bot`:    [(ca_id, nv_id)] người bị rút khỏi ca.
      - `hoan_doi`: mỗi ca có cả người ra lẫn người vào — đây là câu người dùng
        hỏi: "ai bị đổi ca với ai".
      - `doi_giua_hai_ca`: cùng một người RA khỏi ca A và VÀO ca B trong CÙNG một
        lần so sánh. Phải tách khỏi `hoan_doi` vì ý nghĩa hoàn toàn khác: người
        này KHÔNG mất ca, họ chỉ được chuyển sang ca khác.
      - `giu_nguyen`: số ô phân công không đổi.
      - `khong_so_sanh_duoc`: True khi một trong hai bên là None (thiếu dữ liệu).
    """
    if truoc is None or sau is None:
        return {
            "them": [],
            "bot": [],
            "hoan_doi": [],
            "doi_giua_hai_ca": [],
            "giu_nguyen": 0,
            "khong_so_sanh_duoc": True,
        }

    truoc_norm = {str(ca): _as_id_list(ids) for ca, ids in (truoc or {}).items()}
    sau_norm = {str(ca): _as_id_list(ids) for ca, ids in (sau or {}).items()}

    them: list[tuple[str, str]] = []
    bot: list[tuple[str, str]] = []
    giu_nguyen = 0

    for ca_id in sorted(set(truoc_norm) | set(sau_norm)):
        cu = set(truoc_norm.get(ca_id, []))
        moi = set(sau_norm.get(ca_id, []))
        giu_nguyen += len(cu & moi)
        for nv_id in sorted(moi - cu):
            them.append((ca_id, nv_id))
        for nv_id in sorted(cu - moi):
            bot.append((ca_id, nv_id))

    ra_theo_nguoi: dict[str, list[str]] = {}
    for ca_id, nv_id in bot:
        ra_theo_nguoi.setdefault(nv_id, []).append(ca_id)
    vao_theo_nguoi: dict[str, list[str]] = {}
    for ca_id, nv_id in them:
        vao_theo_nguoi.setdefault(nv_id, []).append(ca_id)

    # Chuyển ca: người vừa ra khỏi ca này vừa vào ca khác. Nhãn nói rõ "chuyển",
    # không nói "mất ca" — hai chuyện khác nhau về nghiệp vụ.
    doi_giua_hai_ca: list[dict[str, Any]] = []
    for nv_id in sorted(set(ra_theo_nguoi) & set(vao_theo_nguoi)):
        tu_ca = ra_theo_nguoi[nv_id]
        den_ca = vao_theo_nguoi[nv_id]
        doi_giua_hai_ca.append({
            "nv_id": nv_id,
            "ten": _ten(nv_id, nhan_vien),
            "tu_ca": [_ca_info(c, ca_meta) for c in tu_ca],
            "den_ca": [_ca_info(c, ca_meta) for c in den_ca],
        })

    # Hoán đổi: trong CÙNG một ca có người ra và người vào. Đây là chỗ trả lời
    # "ai bị thay thế bởi ai".
    theo_ca_ra: dict[str, list[str]] = {}
    for ca_id, nv_id in bot:
        theo_ca_ra.setdefault(ca_id, []).append(nv_id)
    theo_ca_vao: dict[str, list[str]] = {}
    for ca_id, nv_id in them:
        theo_ca_vao.setdefault(ca_id, []).append(nv_id)

    hoan_doi: list[dict[str, Any]] = []
    for ca_id in sorted(set(theo_ca_ra) & set(theo_ca_vao)):
        info = _ca_info(ca_id, ca_meta)
        ra_list = [
            {"nv_id": nv, "ten": _ten(nv, nhan_vien)}
            for nv in sorted(theo_ca_ra[ca_id])
        ]
        vao_list = [
            {"nv_id": nv, "ten": _ten(nv, nhan_vien)}
            for nv in sorted(theo_ca_vao[ca_id])
        ]
        hoan_doi.append({"ca": info, "ra": ra_list, "vao": vao_list})

    def _dong(ca_id: str, nv_id: str, chieu: str) -> dict[str, Any]:
        return {
            "ca": _ca_info(ca_id, ca_meta),
            "nv_id": nv_id,
            "ten": _ten(nv_id, nhan_vien),
            "chieu": chieu,
        }

    return {
        "them": [_dong(c, n, "vao") for c, n in them[:gioi_han]],
        "bot": [_dong(c, n, "ra") for c, n in bot[:gioi_han]],
        "hoan_doi": hoan_doi[:gioi_han],
        "doi_giua_hai_ca": doi_giua_hai_ca[:gioi_han],
        "giu_nguyen": giu_nguyen,
        "khong_so_sanh_duoc": False,
    }


def tom_tat_thay_doi(diff: dict[str, Any]) -> str:
    """Một câu tiếng Việt mô tả diff — dùng cho panel và cho trợ lý.

    Trả "" khi không có gì đổi (KHÔNG trả "không có thay đổi" khi thiếu dữ liệu,
    vì đó là hai chuyện khác nhau; xem `khong_so_sanh_duoc`).
    """
    if diff.get("khong_so_sanh_duoc"):
        return "Chưa đủ dữ liệu để so sánh hai bản phân công."
    hoan_doi = diff.get("hoan_doi") or []
    chuyen = diff.get("doi_giua_hai_ca") or []
    them = diff.get("them") or []
    bot = diff.get("bot") or []
    if not (hoan_doi or chuyen or them or bot):
        return "Không có ca nào thay đổi."

    phan: list[str] = []
    if hoan_doi:
        phan.append(f"{len(hoan_doi)} ca đổi người")
    if chuyen:
        phan.append(f"{len(chuyen)} người chuyển sang ca khác")
    so_them = sum(1 for t in them if t not in bot)
    if so_them:
        phan.append(f"{so_them} lượt người vào ca")
    return "; ".join(phan) + "."
