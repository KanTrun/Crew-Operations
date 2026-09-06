#!/usr/bin/env python3
"""CLI Chưng cất Kỹ năng & Kiểm định Toàn vẹn (Distillation & Verification Pipeline).

Tuân thủ phương pháp luận Repo-To-Skill (Scope -> Ground -> Construct -> Verify).
Quét thư mục skills/repositories/repo-skills, thực thi smoke tests và sinh chỉ mục skills_index.jsonl.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
REPO_SKILLS_DIR = SKILLS_ROOT / "repositories" / "repo-skills"


def compute_dir_sha256(dir_path: Path) -> str:
    """Tính toán hash sha256 tổng hợp của thư mục skill."""
    hasher = hashlib.sha256()
    for file_path in sorted(dir_path.rglob("*")):
        if file_path.is_file() and not file_path.name.endswith((".pyc", ".DS_Store")):
            hasher.update(file_path.name.encode("utf-8"))
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


def parse_skill_frontmatter(skill_md_path: Path) -> dict[str, Any]:
    """Phân tích frontmatter đơn giản từ SKILL.md."""
    text = skill_md_path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    metadata[k.strip()] = v.strip().strip('"').strip("'")
    return metadata


def verify_and_index_skills(verify_only: bool = False) -> tuple[bool, list[dict[str, Any]]]:
    """Thực thi pipeline kiểm tra và chỉ mục hóa toàn bộ skill."""
    skills_found: list[dict[str, Any]] = []
    all_passed = True

    search_dir = REPO_SKILLS_DIR if REPO_SKILLS_DIR.exists() else SKILLS_ROOT
    print(f"[*] Quét thư mục kỹ năng tại: {search_dir}")

    # Tìm tất cả các file SKILL.md bên trong repo-skills
    skill_files = list(search_dir.glob("*/SKILL.md"))
    print(f"[*] Tìm thấy {len(skill_files)} định nghĩa SKILL.md\n")

    for skill_file in sorted(skill_files):
        skill_dir = skill_file.parent
        skill_rel_path = skill_dir.relative_to(SKILLS_ROOT)
        skill_id = skill_dir.name

        fm = parse_skill_frontmatter(skill_file)
        name = fm.get("name", skill_id)
        desc = fm.get("description", "")

        print(f"--- Kiểm định: {skill_id} ({skill_rel_path}) ---")

        # 1. Kiểm tra cấu trúc thư mục
        scripts_dir = skill_dir / "scripts"
        refs_dir = skill_dir / "references"
        scripts = [p.name for p in scripts_dir.glob("*.py")] if scripts_dir.exists() else []
        refs = [p.name for p in refs_dir.glob("*.md")] if refs_dir.exists() else []

        print(f"  [+] Scripts: {scripts or 'None'}")
        print(f"  [+] References: {refs or 'None'}")

        # 2. Thực thi Smoke Test các script trong scripts/
        script_test_results: dict[str, bool] = {}
        for script_name in scripts:
            script_path = scripts_dir / script_name
            try:
                proc = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(REPO_ROOT),
                    encoding="utf-8",
                    errors="replace",
                )
                passed = proc.returncode == 0
                script_test_results[script_name] = passed
                status_icon = "PASS" if passed else "FAIL"
                print(f"  [{status_icon}] Test script: {script_name} -> Return code: {proc.returncode}")
                if not passed:
                    print(f"      Chi tiết lỗi: {proc.stderr.strip()[:200]}")
                    all_passed = False
            except Exception as e:
                print(f"  [FAIL] Lỗi thực thi {script_name}: {e}")
                script_test_results[script_name] = False
                all_passed = False

        # 3. Tính content sha256
        dir_hash = compute_dir_sha256(skill_dir)
        print(f"  [#] Content SHA256: {dir_hash[:16]}...")

        is_verified = (all(script_test_results.values()) if script_test_results else True)
        skill_status = "verified" if is_verified else "failed"

        skills_found.append({
            "schema_version": 1,
            "skill_id": skill_id,
            "name": name,
            "description": desc,
            "relative_path": str(skill_rel_path).replace("\\", "/"),
            "scripts": scripts,
            "references": refs,
            "status": skill_status,
            "content_sha256": dir_hash,
        })
        print(f"  [*] Trạng thái kiểm định: {skill_status.upper()}\n")

    # 4. Ghi file index nếu không phải verify_only
    index_file = SKILLS_ROOT / "skills_index.jsonl"
    if not verify_only:
        with open(index_file, "w", encoding="utf-8") as f:
            for item in skills_found:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[OK] Đã cập nhật chỉ mục tại: {index_file}")

    return all_passed, skills_found


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline Chưng cất và Kiểm định Kỹ năng NHỊP QUÁN")
    parser.add_argument("--verify-only", action="store_true", help="Chỉ kiểm tra và trả về exit code, không ghi lại index")
    args = parser.parse_args()

    passed, skills = verify_and_index_skills(verify_only=args.verify_only)

    print("=" * 60)
    print(f"TỔNG KẾT: {len(skills)} Kỹ năng | Trạng thái: {'HOÀN TẤT VÀ HỢP LỆ (VERIFIED)' if passed else 'CÓ LỖI KIỂM ĐỊNH'}")
    print("=" * 60)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
