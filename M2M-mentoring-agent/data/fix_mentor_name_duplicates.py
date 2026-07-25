"""
mentors.json 내 중복된 mentor_info.name만 고유한 이름으로 교체한다.
(matching_summary_text 등 다른 필드는 이름을 언급하지 않으므로 건드리지 않음)

처음 등장한 이름은 그대로 두고, 두 번째 이후 중복부터 새 이름을 배정한다.

실행:
  venv\\Scripts\\python.exe data\\fix_mentor_name_duplicates.py
  venv\\Scripts\\python.exe data\\fix_mentor_name_duplicates.py --dry-run
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MENTORS_DB = ROOT / "json_db" / "mentors.json"

random.seed(7)

SURNAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "남", "심",
]

MALE_GIVEN = [
    "민준", "서준", "도윤", "예준", "시우", "하준", "주원", "지호", "지후", "준서",
    "건우", "현우", "우진", "선우", "연우", "정우", "승우", "동현", "재현", "성민",
    "준영", "민재", "지훈", "태민", "현수", "규민", "성현", "재민", "동욱", "영훈",
    "상현", "재원", "우현", "승현", "준혁", "태윤", "민석", "형준", "찬우", "경민",
]

FEMALE_GIVEN = [
    "서연", "지우", "서윤", "지민", "하윤", "민서", "수아", "예은", "채원", "유진",
    "지유", "다은", "은서", "소율", "예린", "수빈", "지아", "하은", "서현", "가은",
    "민지", "유나", "혜인", "나윤", "다인", "소민", "예지", "지연", "수연", "은지",
    "혜원", "나연", "채은", "시은", "윤서", "가영", "지원", "예나", "수민", "하연",
]


def build_name_pool(given_names: list[str]) -> list[str]:
    pool = [f"{s}{g}" for s in SURNAMES for g in given_names]
    random.shuffle(pool)
    return pool


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = json.loads(MENTORS_DB.read_text(encoding="utf-8"))
    records = db["records"]

    male_pool = iter(build_name_pool(MALE_GIVEN))
    female_pool = iter(build_name_pool(FEMALE_GIVEN))

    used_names: set[str] = set()
    changes: list[dict] = []

    for r in records:
        info = r.get("mentor_info", {})
        name = info.get("name", "")
        gender = info.get("gender", "남")
        pool = male_pool if gender == "남" else female_pool

        if name and name not in used_names:
            used_names.add(name)
            continue

        # 중복(또는 이름 없음) -> 새 이름 배정
        new_name = next(pool)
        while new_name in used_names:
            new_name = next(pool)
        used_names.add(new_name)
        changes.append({
            "mentor_id": r.get("mentor_id"),
            "old_name": name,
            "new_name": new_name,
            "role": r.get("current_role", ""),
        })
        info["name"] = new_name
        r["mentor_info"] = info

    print(f"총 레코드: {len(records)} / 고유 이름 최종: {len(used_names)} / 교체 건수: {len(changes)}")
    for c in changes[:20]:
        print(f"  {c['old_name'] or '(없음)'} -> {c['new_name']}  ({c['role']})")
    if len(changes) > 20:
        print(f"  ... 외 {len(changes) - 20}건")

    if args.dry_run:
        print("dry-run — 파일 저장 안 함")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = MENTORS_DB.with_name(f"mentors.backup_{timestamp}.json")
    shutil.copy2(MENTORS_DB, backup_path)
    print(f"백업 완료: {backup_path}")

    MENTORS_DB.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print("mentors.json 저장 완료")


if __name__ == "__main__":
    main()
