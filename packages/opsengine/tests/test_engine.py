from __future__ import annotations

from ca_ops import add_treo, complete_buoc, escalate, load_template, start_phieu


def test_mo_quan_has_20_steps() -> None:
    tpl = load_template("mo_quan")
    assert len(tpl["buoc"]) >= 20


def test_run_full_phieu_and_treo() -> None:
    run = start_phieu(
        run_id="p1",
        mau="mo_quan",
        nv_id="nv_03",
        ca_id="w1_c01",
        now_ms=0,
        diem_danh=True,
    )
    t = 1000
    photo = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
    for b in list(run.buoc):
        if b.minh_chung == "anh":
            val: object = photo
        elif b.minh_chung in {"so", "kiem_ke"}:
            val = "4"
        else:
            val = True
        complete_buoc(run, b.ma, val, t)
        t += 1000
    assert run.closed
    add_treo(run, "hết sữa tươi")
    assert run.treo == ["hết sữa tươi"]
    assert escalate(run, now_ms=31 * 60_000) == "nhac_nhan_vien"
