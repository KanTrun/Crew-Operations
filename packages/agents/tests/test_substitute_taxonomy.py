"""Unit test cho taxonomy nhóm món thay thế nạp từ config (plan mục 1.2 / 3.4).

Plan mục 3.4: ma trận nhu cầu → nhóm thay thế phải là DỮ LIỆU CẤU HÌNH versioned,
KHÔNG hard-code trong logic nghiệp vụ. Test này chứng minh:

1. `normalize_category_name` tất định và không suy đoán.
2. `parse_taxonomy` fail-fast khi file thiếu/trùng/chồng lấn trường bắt buộc.
3. `entries_cho_duyet` KHÔNG được nạp (plan mục 1.5 — agent không tự chốt thay
   chủ dự án các nhóm chưa duyệt).
4. `SubstituteTaxonomyIndex` tra cứu đúng ma trận 4 dòng của plan mục 1.2.
5. File `config/substitute-taxonomy.yaml` thật khớp đúng ma trận plan.
6. `union_core_and_substitutes` cho thứ tự tất định (ADR-002).

Không network, không LLM. Dữ liệu trong fixture là DỮ LIỆU MÔ PHỎNG.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ca_agents.ag_pricing.substitute_taxonomy import (
    ROOT,
    TAXONOMY_PATH,
    SubstituteTaxonomyError,
    SubstituteTaxonomyIndex,
    TaxonomyGroup,
    load_taxonomy,
    normalize_category_name,
    parse_taxonomy,
    union_core_and_substitutes,
)
from ca_contracts.catchment_survey_v2 import SubstituteTaxonomy


def _entry(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "jtbd_group": "lunch_meal_replacement",
        "mo_ta": "Bữa trưa no bụng",
        "nhom_lam_tron": "mon_chinh",
        "version": 1,
        "core_categories": ["com_tam", "com_suon"],
        "substitute_categories": ["bun_bo_hue", "pho_bo"],
    }
    base.update(overrides)
    return base


def _du_lieu_chuan() -> dict[str, Any]:
    return {"schema_version": 1, "entries": [_entry()]}


# ── 1. normalize_category_name ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "ket_qua"),
    [
        ("Cơm Sườn Bì Chả", "com_suon_bi_cha"),
        ("cơm tấm", "com_tam"),
        ("Bún Bò Huế", "bun_bo_hue"),
        ("Phở", "pho"),
        ("Đặc Sản", "dac_san"),
        ("Cà Phê Muối", "ca_phe_muoi"),
        ("bánh_tráng-trộn", "banh_trang_tron"),
        ("Trà Sữa / Milk Tea", "tra_sua_milk_tea"),
        ("  com tam  ", "com_tam"),
        ("", ""),
        ("   ", ""),
        ("!!!", ""),
    ],
)
def test_normalize_category_name_chuan_hoa_dung(raw: str, ket_qua: str) -> None:
    assert normalize_category_name(raw) == ket_qua


def test_normalize_category_name_la_tat_dinh() -> None:
    """ADR-002: cùng input → cùng output, không phụ thuộc locale/seed."""
    for _ in range(3):
        assert normalize_category_name("Cơm Tấm Sườn") == "com_tam_suon"


def test_normalize_category_name_idempotent() -> None:
    """Chuẩn hoá hai lần không đổi kết quả (quan trọng khi so khớp OCR output)."""
    mot_lan = normalize_category_name("Bún Bò Huế")
    assert normalize_category_name(mot_lan) == mot_lan


# ── 2. parse_taxonomy — fail-fast ─────────────────────────────────────────────


def test_parse_fixture_chuan() -> None:
    taxonomy, groups = parse_taxonomy(_du_lieu_chuan())

    assert isinstance(taxonomy, SubstituteTaxonomy)
    assert taxonomy.schema_version == 1
    assert len(taxonomy.entries) == 1
    assert taxonomy.entries[0].jtbd_group == "lunch_meal_replacement"
    assert taxonomy.entries[0].core_categories == ["com_tam", "com_suon"]
    assert taxonomy.entries[0].substitute_categories == ["bun_bo_hue", "pho_bo"]
    assert taxonomy.entries[0].version == 1

    assert set(groups) == {"lunch_meal_replacement"}
    nhom = groups["lunch_meal_replacement"]
    assert isinstance(nhom, TaxonomyGroup)
    assert nhom.jtbd_group == "lunch_meal_replacement"
    assert nhom.mo_ta == "Bữa trưa no bụng"
    assert nhom.nhom_lam_tron == "mon_chinh"
    assert nhom.version == 1
    assert nhom.core_categories == ("com_tam", "com_suon")
    assert nhom.substitute_categories == ("bun_bo_hue", "pho_bo")


def test_parse_goc_khong_phai_mapping() -> None:
    with pytest.raises(SubstituteTaxonomyError, match="mapping ở gốc"):
        parse_taxonomy(["khong", "phai", "dict"])


def test_parse_khong_co_entries_thi_tra_taxonomy_rong() -> None:
    """File chưa khai báo nhóm nào không phải lỗi cấu trúc — chỉ là taxonomy rỗng."""
    taxonomy, groups = parse_taxonomy({"schema_version": 1})
    assert taxonomy.entries == []
    assert groups == {}


def test_parse_entries_khong_phai_danh_sach() -> None:
    with pytest.raises(SubstituteTaxonomyError, match="entries"):
        parse_taxonomy({"schema_version": 1, "entries": "com_tam"})


def test_parse_phan_tu_entries_khong_phai_mapping() -> None:
    with pytest.raises(SubstituteTaxonomyError, match=r"entries\[0\]"):
        parse_taxonomy({"schema_version": 1, "entries": ["com_tam"]})


def test_parse_thieu_jtbd_group() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0].pop("jtbd_group")
    with pytest.raises(SubstituteTaxonomyError, match="jtbd_group"):
        parse_taxonomy(du_lieu)


def test_parse_jtbd_group_rong() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["jtbd_group"] = "   "
    with pytest.raises(SubstituteTaxonomyError, match="jtbd_group"):
        parse_taxonomy(du_lieu)


def test_parse_trung_jtbd_group() -> None:
    du_lieu = {
        "schema_version": 1,
        "entries": [_entry(), _entry(mo_ta="bản trùng")],
    }
    with pytest.raises(SubstituteTaxonomyError, match="trùng jtbd_group"):
        parse_taxonomy(du_lieu)


def test_parse_core_rong() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["core_categories"] = []
    with pytest.raises(SubstituteTaxonomyError, match="core_categories"):
        parse_taxonomy(du_lieu)


def test_parse_substitute_rong() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["substitute_categories"] = []
    with pytest.raises(SubstituteTaxonomyError, match="substitute_categories"):
        parse_taxonomy(du_lieu)


def test_parse_core_va_substitute_chong_lan() -> None:
    """Một món không thể vừa là lõi vừa là thay thế của chính nó."""
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["substitute_categories"] = ["com_tam", "pho_bo"]
    with pytest.raises(SubstituteTaxonomyError, match="com_tam"):
        parse_taxonomy(du_lieu)


def test_parse_chong_lan_phat_hien_du_khac_cach_viet() -> None:
    """Normalization chạy TRƯỚC khi so chồng lấn nên 'Cơm Tấm' == 'com_tam'."""
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["substitute_categories"] = ["Cơm Tấm"]
    with pytest.raises(SubstituteTaxonomyError, match="com_tam"):
        parse_taxonomy(du_lieu)


@pytest.mark.parametrize("version_sai", [0, -1, "1", 1.5, None, True])
def test_parse_version_phai_la_so_nguyen_lon_hon_hoac_bang_1(version_sai: Any) -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["version"] = version_sai
    with pytest.raises(SubstituteTaxonomyError, match="version"):
        parse_taxonomy(du_lieu)


@pytest.mark.parametrize("schema_sai", [0, -1, "1", None, True])
def test_parse_schema_version_phai_la_so_nguyen_lon_hon_hoac_bang_1(schema_sai: Any) -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["schema_version"] = schema_sai
    with pytest.raises(SubstituteTaxonomyError, match="schema_version"):
        parse_taxonomy(du_lieu)


def test_parse_schema_version_mac_dinh_la_1() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu.pop("schema_version")
    taxonomy, _ = parse_taxonomy(du_lieu)
    assert taxonomy.schema_version == 1


def test_parse_nhom_lam_tron_mac_dinh_la_mon_chinh() -> None:
    """Không khai báo → mặc định món chính (bội 5.000đ, an toàn hơn 1.000đ)."""
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0].pop("nhom_lam_tron")
    _, groups = parse_taxonomy(du_lieu)
    assert groups["lunch_meal_replacement"].nhom_lam_tron == "mon_chinh"


def test_parse_nhom_lam_tron_sai_kieu() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["nhom_lam_tron"] = 5000
    with pytest.raises(SubstituteTaxonomyError, match="nhom_lam_tron"):
        parse_taxonomy(du_lieu)


def test_parse_mo_ta_sai_kieu() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["mo_ta"] = 42
    with pytest.raises(SubstituteTaxonomyError, match="mo_ta"):
        parse_taxonomy(du_lieu)


def test_parse_alias_khong_phai_mapping() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["alias"] = ["cơm tấm"]
    with pytest.raises(SubstituteTaxonomyError, match="alias"):
        parse_taxonomy(du_lieu)


def test_parse_alias_gia_tri_khong_phai_danh_sach_chuoi() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["alias"] = {"com_tam": "cơm tấm"}
    with pytest.raises(SubstituteTaxonomyError, match="alias"):
        parse_taxonomy(du_lieu)


def test_parse_alias_khoa_rong() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["alias"] = {"!!!": ["cơm tấm"]}
    with pytest.raises(SubstituteTaxonomyError, match="khóa alias rỗng"):
        parse_taxonomy(du_lieu)


def test_parse_alias_duoc_chuan_hoa_ca_khoa_lan_gia_tri() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["alias"] = {"Cơm Tấm": ["Cơm Sườn Bì Chả", "com tam"]}
    _, groups = parse_taxonomy(du_lieu)
    assert groups["lunch_meal_replacement"].alias == {
        "com_tam": ("com_suon_bi_cha", "com_tam")
    }


def test_parse_danh_sach_chuoi_co_phan_tu_rong() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["core_categories"] = ["com_tam", ""]
    with pytest.raises(SubstituteTaxonomyError, match="core_categories"):
        parse_taxonomy(du_lieu)


def test_parse_danh_sach_chuoi_khong_phai_danh_sach() -> None:
    du_lieu = _du_lieu_chuan()
    du_lieu["entries"][0]["core_categories"] = "com_tam"
    with pytest.raises(SubstituteTaxonomyError, match="core_categories"):
        parse_taxonomy(du_lieu)


# ── 3. entries_cho_duyet KHÔNG được nạp (plan mục 1.5) ────────────────────────


def test_entries_cho_duyet_khong_duoc_nap() -> None:
    """Agent không tự chốt thay chủ dự án nhóm nhu cầu chưa được duyệt."""
    du_lieu = _du_lieu_chuan()
    du_lieu["entries_cho_duyet"] = [
        _entry(
            jtbd_group="vegetarian_meal",
            core_categories=["com_chay", "bun_chay"],
            substitute_categories=["pho_chay"],
        )
    ]
    taxonomy, groups = parse_taxonomy(du_lieu)

    assert set(groups) == {"lunch_meal_replacement"}
    assert [e.jtbd_group for e in taxonomy.entries] == ["lunch_meal_replacement"]
    assert "vegetarian_meal" not in groups


def test_entries_cho_duyet_van_duoc_kiem_tra_cau_truc() -> None:
    """Bỏ qua ≠ không kiểm tra: file sai cú pháp ở section chờ duyệt vẫn phải báo lỗi."""
    du_lieu = _du_lieu_chuan()
    du_lieu["entries_cho_duyet"] = "khong-phai-danh-sach"
    with pytest.raises(SubstituteTaxonomyError, match="entries_cho_duyet"):
        parse_taxonomy(du_lieu)


def test_file_that_co_section_cho_duyet_va_khong_nap_no() -> None:
    _, groups = load_taxonomy()
    assert "vegetarian_meal" not in groups
    assert "low_carb_meal" not in groups


# ── 4. load_taxonomy ──────────────────────────────────────────────────────────


def test_duong_dan_file_that_dung_quy_uoc_repo() -> None:
    assert TAXONOMY_PATH == ROOT / "config" / "substitute-taxonomy.yaml"
    assert TAXONOMY_PATH.exists(), f"thiếu file taxonomy: {TAXONOMY_PATH}"


def test_load_file_khong_ton_tai(tmp_path: Path) -> None:
    with pytest.raises(SubstituteTaxonomyError, match="không tìm thấy file taxonomy"):
        load_taxonomy(tmp_path / "khong-ton-tai.yaml")


def test_load_file_tam(tmp_path: Path) -> None:
    """Loader đọc được file ở đường dẫn bất kỳ, không chỉ file mặc định."""
    p = tmp_path / "taxonomy.yaml"
    p.write_text(
        "schema_version: 2\n"
        "entries:\n"
        "  - jtbd_group: 'snack_afternoon'\n"
        "    version: 3\n"
        "    core_categories: ['banh_trang_tron']\n"
        "    substitute_categories: ['che']\n",
        encoding="utf-8",
    )
    taxonomy, groups = load_taxonomy(p)
    assert taxonomy.schema_version == 2
    assert groups["snack_afternoon"].version == 3


# ── 5. File config thật khớp ma trận plan mục 1.2 ─────────────────────────────


def test_file_that_co_du_bon_nhom_jtbd_cua_plan() -> None:
    """Plan mục 1.2 liệt kê đúng 4 dòng nhu cầu → 4 nhóm đang hoạt động."""
    taxonomy, groups = load_taxonomy()
    assert taxonomy.schema_version >= 1
    assert set(groups) == {
        "lunch_meal_replacement",
        "beverage_third_place",
        "snack_afternoon",
        "gathering_dinner",
    }
    assert len(taxonomy.entries) == 4


def test_file_that_dong_1_bua_trua_no_bung() -> None:
    """Plan mục 1.2: Cơm ↔ Bún, Phở, Hủ tiếu, Bánh canh, Mì Quảng, Bánh mì."""
    _, groups = load_taxonomy()
    nhom = groups["lunch_meal_replacement"]
    assert "com_tam" in nhom.core_categories
    for mon_thay_the in ("bun_bo_hue", "pho_bo", "hu_tieu", "banh_canh", "mi_quang", "banh_mi"):
        assert mon_thay_the in nhom.substitute_categories, f"thiếu {mon_thay_the}"
    assert nhom.nhom_lam_tron == "mon_chinh"


def test_file_that_dong_2_thuc_uong_lam_viec() -> None:
    """Plan mục 1.2: Cà phê ↔ Trà trái cây, Trà sữa, Nước ép/sinh tố."""
    _, groups = load_taxonomy()
    nhom = groups["beverage_third_place"]
    assert "ca_phe" in nhom.core_categories
    for mon_thay_the in ("tra_trai_cay", "tra_sua", "nuoc_ep", "sinh_to"):
        assert mon_thay_the in nhom.substitute_categories, f"thiếu {mon_thay_the}"
    # Đồ uống làm tròn bội 1.000đ (plan mục 1.5.7)
    assert nhom.nhom_lam_tron == "beverage"


def test_file_that_dong_3_an_xe() -> None:
    """Plan mục 1.2: Bánh tráng trộn ↔ Chè, Kem, Cá viên chiên, Gà rán."""
    _, groups = load_taxonomy()
    nhom = groups["snack_afternoon"]
    assert "banh_trang_tron" in nhom.core_categories
    for mon_thay_the in ("che", "kem", "ca_vien_chien", "ga_ran"):
        assert mon_thay_the in nhom.substitute_categories, f"thiếu {mon_thay_the}"


def test_file_that_dong_4_tu_tap_bua_toi() -> None:
    """Plan mục 1.2: Lẩu ↔ BBQ nướng, Quán ốc, Quán nhậu bình dân."""
    _, groups = load_taxonomy()
    nhom = groups["gathering_dinner"]
    assert "lau" in nhom.core_categories
    for mon_thay_the in ("bbq_nuong", "quan_oc", "quan_nhau"):
        assert mon_thay_the in nhom.substitute_categories, f"thiếu {mon_thay_the}"


def test_file_that_moi_nhom_deu_co_version() -> None:
    """Plan mục 3.4: config phải versioned để truy vết kết quả khảo sát."""
    _, groups = load_taxonomy()
    for key, nhom in groups.items():
        assert nhom.version >= 1, f"{key} thiếu version"


def test_file_that_khong_hard_code_trong_ma() -> None:
    """Ma trận nằm ở config; `substitute_matrix.py` (v1.0) không phải nguồn sự thật."""
    noi_dung = TAXONOMY_PATH.read_text(encoding="utf-8")
    assert "KHÔNG hard-code" in noi_dung or "không hard-code" in noi_dung.lower()
    assert "substitute_matrix.py" in noi_dung


# ── 6. SubstituteTaxonomyIndex ────────────────────────────────────────────────


def _index_fixture() -> SubstituteTaxonomyIndex:
    du_lieu = {
        "schema_version": 1,
        "entries": [
            _entry(),
            _entry(
                jtbd_group="beverage_third_place",
                mo_ta="Thức uống",
                nhom_lam_tron="beverage",
                version=2,
                core_categories=["ca_phe"],
                substitute_categories=["tra_sua", "tra_trai_cay"],
                alias={"ca_phe": ["cà phê", "cafe"]},
            ),
        ],
    }
    taxonomy, groups = parse_taxonomy(du_lieu)
    return SubstituteTaxonomyIndex(taxonomy, groups)


def test_index_from_file_doc_duoc_file_that() -> None:
    index = SubstituteTaxonomyIndex.from_file()
    assert index.group("lunch_meal_replacement") is not None


def test_index_group_tra_ve_none_khong_biet() -> None:
    index = _index_fixture()
    assert index.group("khong_ton_tai") is None


def test_index_groups_giu_dung_thu_tu_config() -> None:
    index = _index_fixture()
    assert [g.jtbd_group for g in index.groups] == [
        "lunch_meal_replacement", "beverage_third_place"
    ]


def test_index_resolve_category_tim_dung_ten_chuan() -> None:
    index = _index_fixture()
    assert index.resolve_category("com_tam") == "com_tam"
    assert index.resolve_category("ca_phe") == "ca_phe"


def test_index_resolve_category_qua_alias_co_dau() -> None:
    index = _index_fixture()
    assert index.resolve_category("Cà Phê") == "ca_phe"
    assert index.resolve_category("cafe") == "ca_phe"


def test_index_resolve_category_khong_suy_doan() -> None:
    """Tên không có trong config → None, để caller xếp 'mon_khac' (ADR-002)."""
    index = _index_fixture()
    assert index.resolve_category("pizza") is None
    assert index.resolve_category("") is None
    assert index.resolve_category("!!!") is None


def test_index_substitute_categories_dung_ma_tran() -> None:
    index = _index_fixture()
    assert index.substitute_categories("com_tam") == ("bun_bo_hue", "pho_bo")
    assert index.substitute_categories("ca_phe") == ("tra_sua", "tra_trai_cay")


def test_index_substitute_categories_mon_khong_phai_core() -> None:
    index = _index_fixture()
    assert index.substitute_categories("bun_bo_hue") == ()
    assert index.substitute_categories("pizza") == ()


def test_index_substitute_categories_chap_nhan_ten_co_dau() -> None:
    index = _index_fixture()
    assert index.substitute_categories("Cơm Tấm") == ("bun_bo_hue", "pho_bo")


def test_index_groups_for_core_nhieu_nhop_khop() -> None:
    """Một món lõi có thể thuộc nhiều nhóm JTBD — phải trả tất cả, theo thứ tự config."""
    du_lieu = {
        "schema_version": 1,
        "entries": [
            _entry(jtbd_group="nhom_a", core_categories=["com_tam"],
                   substitute_categories=["pho_bo"]),
            _entry(jtbd_group="nhom_b", core_categories=["com_tam"],
                   substitute_categories=["banh_mi"]),
        ],
    }
    taxonomy, groups = parse_taxonomy(du_lieu)
    index = SubstituteTaxonomyIndex(taxonomy, groups)

    assert [g.jtbd_group for g in index.groups_for_core("com_tam")] == ["nhom_a", "nhom_b"]
    assert index.substitute_categories("com_tam") == ("pho_bo", "banh_mi")


def test_index_substitute_categories_khu_trung() -> None:
    du_lieu = {
        "schema_version": 1,
        "entries": [
            _entry(jtbd_group="nhom_a", core_categories=["com_tam"],
                   substitute_categories=["pho_bo", "banh_mi"]),
            _entry(jtbd_group="nhom_b", core_categories=["com_tam"],
                   substitute_categories=["pho_bo"]),
        ],
    }
    taxonomy, groups = parse_taxonomy(du_lieu)
    index = SubstituteTaxonomyIndex(taxonomy, groups)
    assert index.substitute_categories("com_tam") == ("pho_bo", "banh_mi")


def test_index_rounding_group_theo_nhom() -> None:
    index = _index_fixture()
    assert index.rounding_group("com_tam") == "mon_chinh"
    assert index.rounding_group("ca_phe") == "beverage"


def test_index_rounding_group_mac_dinh_khong_khop() -> None:
    index = _index_fixture()
    assert index.rounding_group("pizza") == "mon_chinh"


def test_index_all_categories_khu_trung_va_sap_xep() -> None:
    index = _index_fixture()
    cats = index.all_categories()
    assert cats == tuple(sorted(set(cats)))
    assert "com_tam" in cats and "tra_sua" in cats


def test_index_versions_dung_cho_observability() -> None:
    """Plan mục 9: version từng nhóm phải truy vết được trong kết quả khảo sát."""
    index = _index_fixture()
    assert index.versions() == {"lunch_meal_replacement": 1, "beverage_third_place": 2}


def test_index_taxonomy_property_giu_contract_pydantic() -> None:
    index = _index_fixture()
    assert isinstance(index.taxonomy, SubstituteTaxonomy)
    # Contract serialize được → gắn vào response/truy vết được
    assert index.taxonomy.model_dump()["schema_version"] == 1


def test_index_alias_khong_de_trung_lap_giua_cac_nhom() -> None:
    """Alias trỏ về category chuẩn; nhóm khai báo trước thắng (tất định)."""
    du_lieu = {
        "schema_version": 1,
        "entries": [
            _entry(jtbd_group="nhom_a", core_categories=["com_tam"],
                   substitute_categories=["pho_bo"], alias={"com_tam": ["cơm tấm"]}),
            _entry(jtbd_group="nhom_b", core_categories=["com_suon"],
                   substitute_categories=["bun_bo"], alias={"com_tam": ["cơm tấm"]}),
        ],
    }
    taxonomy, groups = parse_taxonomy(du_lieu)
    index = SubstituteTaxonomyIndex(taxonomy, groups)
    assert index.resolve_category("cơm tấm") == "com_tam"


def test_taxonomy_group_alias_mac_dinh_la_mapping_rong() -> None:
    nhom = TaxonomyGroup(
        entry=parse_taxonomy(_du_lieu_chuan())[0].entries[0],
    )
    assert nhom.alias == {}
    assert nhom.mo_ta == ""
    assert nhom.nhom_lam_tron == "mon_chinh"


# ── 7. union_core_and_substitutes ─────────────────────────────────────────────


def test_union_gop_core_truoc_roi_den_substitute() -> None:
    ket_qua = union_core_and_substitutes(
        [40000.0, 42000.0],
        {"pho_bo": [55000.0], "bun_bo_hue": [48000.0]},
    )
    # Thứ tự tất định: core, rồi substitute theo khóa đã sort
    assert ket_qua == [40000.0, 42000.0, 48000.0, 55000.0]


def test_union_tat_dinh_khong_phu_thuoc_thu_tu_dict() -> None:
    """ADR-002: Python dict giữ thứ tự chèn — hàm phải sort để không phụ thuộc."""
    a = union_core_and_substitutes([1.0], {"z": [2.0], "a": [3.0]})
    b = union_core_and_substitutes([1.0], {"a": [3.0], "z": [2.0]})
    assert a == b == [1.0, 3.0, 2.0]


def test_union_loc_theo_include_categories() -> None:
    """Plan mục 1.5.3: chỉ gộp các nhóm cùng `positioning_tier`."""
    ket_qua = union_core_and_substitutes(
        [40000.0],
        {"pho_bo": [55000.0], "bun_bo_hue": [48000.0]},
        include_categories=["pho_bo"],
    )
    assert ket_qua == [40000.0, 55000.0]


def test_union_include_categories_rong_chi_con_core() -> None:
    ket_qua = union_core_and_substitutes([40000.0], {"pho_bo": [55000.0]},
                                         include_categories=[])
    assert ket_qua == [40000.0]


def test_union_khong_co_substitute() -> None:
    assert union_core_and_substitutes([40000.0], {}) == [40000.0]


def test_union_rong_hoan_toan() -> None:
    assert union_core_and_substitutes([], {}) == []


def test_union_doi_nguyen_sang_float() -> None:
    ket_qua = union_core_and_substitutes([40000], {"pho_bo": [55000]})
    assert ket_qua == [40000.0, 55000.0]
    assert all(isinstance(p, float) for p in ket_qua)


def test_union_khong_dot_chay_input() -> None:
    core = [40000.0]
    subs: dict[str, list[float]] = {"pho_bo": [55000.0]}
    union_core_and_substitutes(core, subs)
    assert core == [40000.0]
    assert subs == {"pho_bo": [55000.0]}
