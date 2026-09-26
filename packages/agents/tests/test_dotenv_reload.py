# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Test cho `ensure_dotenv` — nạp .env và NẠP LẠI khi file bị sửa.

Vì sao quan trọng: người vận hành dán key mới vào `.env` trong lúc API đang chạy.
Nếu tiến trình chỉ đọc `.env` một lần lúc khởi động, nó giữ key CŨ và mọi lượt
gọi đều hỏng cho tới khi khởi động lại — trong khi `.env` trông đã đúng, nên
nguyên nhân rất khó đoán.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from ca_agents import llm


@pytest.fixture
def env_sach(monkeypatch: pytest.MonkeyPatch):
    """Đưa module về trạng thái 'chưa nạp .env', không dính trạng thái test trước."""
    monkeypatch.setattr(llm, "_DOTENV_LOADED", False)
    monkeypatch.setattr(llm, "_DOTENV_PATH", None)
    monkeypatch.setattr(llm, "_DOTENV_MTIME", 0.0)
    monkeypatch.setattr(llm, "_DOTENV_KEYS", set())
    yield


def _ghi_env(path: Path, noi_dung: str) -> None:
    path.write_text(noi_dung, encoding="utf-8")


def test_loads_values_from_file(tmp_path: Path, env_sach, monkeypatch) -> None:
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_A=gia-tri-a\nTEST_KEY_B='co-nhay-don'\n")
    monkeypatch.delenv("TEST_KEY_A", raising=False)
    monkeypatch.delenv("TEST_KEY_B", raising=False)

    llm.load_dotenv(env)

    assert os.environ["TEST_KEY_A"] == "gia-tri-a"
    # Nháy đơn/kép phải được gỡ: người dùng hay dán kèm nháy.
    assert os.environ["TEST_KEY_B"] == "co-nhay-don"


def test_existing_process_env_wins(tmp_path: Path, env_sach, monkeypatch) -> None:
    """Biến của môi trường tiến trình (CI, shell export) thắng .env."""
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_C=tu-file\n")
    monkeypatch.setenv("TEST_KEY_C", "tu-moi-truong")

    llm.load_dotenv(env)

    assert os.environ["TEST_KEY_C"] == "tu-moi-truong"


def test_env_key_not_marked_as_dotenv_owned(tmp_path: Path, env_sach, monkeypatch) -> None:
    """Biến đã có trong môi trường KHÔNG được coi là 'của .env'.

    Nếu đánh dấu nhầm, lần nạp lại sau sẽ ghi đè cả biến của CI — đúng thứ mà
    quy tắc 'môi trường thắng .env' sinh ra để ngăn.
    """
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_D=tu-file\nTEST_KEY_E=tu-file\n")
    monkeypatch.setenv("TEST_KEY_E", "tu-moi-truong")
    monkeypatch.delenv("TEST_KEY_D", raising=False)

    llm.load_dotenv(env)

    assert "TEST_KEY_D" in llm._DOTENV_KEYS
    assert "TEST_KEY_E" not in llm._DOTENV_KEYS


def test_ensure_dotenv_reloads_after_file_change(tmp_path: Path, env_sach, monkeypatch) -> None:
    """ĐÂY LÀ BUG ĐÃ SỬA: sửa .env xong gọi lại phải thấy giá trị MỚI.

    Kịch bản thật: hết hạn mức Cloudflare → dán key mới vào .env → bấm tạo ảnh
    lại. Trước khi sửa, tiến trình vẫn dùng key cũ và chỉ rơi xuống provider dự
    phòng, còn .env thì trông đã đúng.
    """
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_F=key-cu\n")
    monkeypatch.delenv("TEST_KEY_F", raising=False)
    llm.load_dotenv(env)
    assert os.environ["TEST_KEY_F"] == "key-cu"

    # Người vận hành dán key mới. mtime phải khác đi để phát hiện thay đổi —
    # ghi rõ mtime chứ không dựa vào độ phân giải đồng hồ của hệ điều hành.
    _ghi_env(env, "TEST_KEY_F=key-moi\n")
    os.utime(env, (llm._DOTENV_MTIME + 10, llm._DOTENV_MTIME + 10))

    llm.ensure_dotenv()

    assert os.environ["TEST_KEY_F"] == "key-moi"


def test_ensure_dotenv_skips_reread_when_unchanged(tmp_path: Path, env_sach, monkeypatch) -> None:
    """File không đổi → KHÔNG đọc lại (gọi hàm này trên mọi lượt gọi provider)."""
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_G=goc\n")
    monkeypatch.delenv("TEST_KEY_G", raising=False)
    llm.load_dotenv(env)

    # Sửa biến trong bộ nhớ tay: nếu đọc lại file thì giá trị sẽ bị ghi đè về 'goc'.
    os.environ["TEST_KEY_G"] = "sua-tay"
    llm.ensure_dotenv()

    assert os.environ["TEST_KEY_G"] == "sua-tay"


def test_ensure_dotenv_keeps_values_when_file_deleted(tmp_path: Path, env_sach, monkeypatch) -> None:
    """`.env` bị xoá → GIỮ giá trị đang có, không xoá credential khỏi bộ nhớ.

    Mất credential đột ngột giữa chừng làm tính năng hỏng theo cách khó hiểu hơn
    là tiếp tục dùng giá trị đã nạp.
    """
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_H=con-dung\n")
    monkeypatch.delenv("TEST_KEY_H", raising=False)
    llm.load_dotenv(env)
    assert os.environ["TEST_KEY_H"] == "con-dung"

    env.unlink()
    llm.ensure_dotenv()

    assert os.environ["TEST_KEY_H"] == "con-dung"


def test_ensure_dotenv_removes_key_deleted_from_file(tmp_path: Path, env_sach, monkeypatch) -> None:
    """Xoá một dòng khỏi .env → biến đó phải biến mất, không giữ giá trị cũ.

    Cần thiết để 'bỏ key' có tác dụng thật (ví dụ ngừng dùng một provider).
    """
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_I=se-bi-xoa\nTEST_KEY_J=giu-lai\n")
    monkeypatch.delenv("TEST_KEY_I", raising=False)
    monkeypatch.delenv("TEST_KEY_J", raising=False)
    llm.load_dotenv(env)
    assert os.environ["TEST_KEY_I"] == "se-bi-xoa"

    _ghi_env(env, "TEST_KEY_J=giu-lai\n")
    os.utime(env, (llm._DOTENV_MTIME + 10, llm._DOTENV_MTIME + 10))
    llm.ensure_dotenv()

    assert "TEST_KEY_I" not in os.environ
    assert os.environ["TEST_KEY_J"] == "giu-lai"


def test_ensure_dotenv_does_not_override_ci_env_on_reload(
    tmp_path: Path, env_sach, monkeypatch
) -> None:
    """Nạp lại KHÔNG được ghi đè biến do CI/môi trường đặt (quy tắc cũ giữ nguyên).

    CI ép `CA_AGENT_MODE=replay`; nếu lần nạp lại ghi đè thành `live`, test sẽ
    gọi mạng thật — phá vỡ cả bộ test.
    """
    env = tmp_path / ".env"
    _ghi_env(env, "TEST_KEY_K=tu-file\nCA_AGENT_MODE=live\n")
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    monkeypatch.delenv("TEST_KEY_K", raising=False)
    llm.load_dotenv(env)
    assert os.environ["CA_AGENT_MODE"] == "replay"

    _ghi_env(env, "TEST_KEY_K=tu-file-moi\nCA_AGENT_MODE=live\n")
    os.utime(env, (llm._DOTENV_MTIME + 10, llm._DOTENV_MTIME + 10))
    llm.ensure_dotenv()

    assert os.environ["TEST_KEY_K"] == "tu-file-moi"
    assert os.environ["CA_AGENT_MODE"] == "replay"
