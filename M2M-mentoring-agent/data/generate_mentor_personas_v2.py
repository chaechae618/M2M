"""
멘토 페르소나 200명 추가 생성 (v2 — AI/데이터분석 편중 + 세부 다양성)

기존 mentors.json(50명)에 이어붙인다 (덮어쓰지 않음).
분포:
  - AI/데이터분석 계열 120명 (ML/DL 20, CV 10, NLP/LLM 15, MLOps 10,
    데이터사이언티스트 15, 데이터분석가 25, 데이터엔지니어 15, AI/데이터 PM 10)
  - IT개발(비AI) 40명 (백엔드 10, 프론트엔드 5, 게임개발 5, QA 5, 클라우드/인프라 5, IT PM 10)
  - 기타 도메인 40명 (금융/마케팅/전략/HR/디자인/제조 등 — 기존 MENTOR_SPECS 스타일 유지)

획일화 방지: 슬롯마다 학교·전공·회사·연차·커리어 경로를 무작위 조합해
동일 패턴이 반복되지 않도록 한다.

실행:
  venv\\Scripts\\python.exe data\\generate_mentor_personas_v2.py
  venv\\Scripts\\python.exe data\\generate_mentor_personas_v2.py --dry-run   # spec만 생성, LLM 호출 없음
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.generate_personas import generate_mentor  # noqa: E402

random.seed(42)

MENTORS_DB = ROOT / "json_db" / "mentors.json"

# ─────────────────────────────────────────
# 공통 풀
# ─────────────────────────────────────────

SCHOOLS = [
    "서울대", "연세대", "고려대", "카이스트", "포스텍", "한양대", "성균관대",
    "이화여대", "서강대", "경희대", "중앙대", "UNIST", "GIST", "부산대",
    "인하대", "건국대", "동국대",
]

MAJORS_AI = [
    "컴퓨터공학", "인공지능학", "산업공학", "통계학", "수학", "물리학",
    "전자공학", "데이터사이언스학", "소프트웨어학", "응용수학",
]
MAJORS_NON_TECH = ["경영학", "경제학", "심리학", "사회학", "언론정보학", "생명과학"]

CAREER_PATH_TEMPLATES = [
    "{school} {major} 졸업 후 스타트업 인턴을 거쳐 {company} 입사",
    "{school} {major} 대학원 석사 후 {company} 연구직으로 커리어 시작",
    "{school} {major} 졸업, 부트캠프 수료 후 {company}{josa} 커리어 전환",
    "{school} {major}(비전공) 출신, 독학으로 전환하여 {company} 입사",
    "{school} {major} 졸업 후 대기업 공채로 입사, 이후 {company}{josa} 이직",
    "{school} {major} 졸업, 해외 인턴십 경험 후 {company} 합류",
    "{school} {major} 졸업 후 창업 경험을 거쳐 {company} 합류",
    "{school} {major} 졸업, 첫 직장에서부터 꾸준히 {company}까지 한 우물",
]

AI_COMPANIES = [
    "네이버", "카카오", "쿠팡", "토스", "라인플러스", "우아한형제들(배민)",
    "당근마켓", "야놀자", "업스테이지", "뤼튼테크놀로지스", "스캐터랩",
    "몰로코", "센드버드", "하이퍼커넥트", "마켓컬리", "두나무(업비트)",
    "뱅크샐러드", "왓챠", "리디", "버킷플레이스(오늘의집)", "NC소프트",
    "크래프톤", "삼성전자 AI연구소", "LG AI연구원", "SK텔레콤 AI",
    "KT AI연구소", "구글 코리아", "메타 코리아", "아마존 코리아",
    "마이크로소프트 코리아", "코난테크놀로지", "마인즈랩",
]

IT_COMPANIES = [
    "네이버", "카카오", "토스", "쿠팡", "당근마켓", "라인플러스",
    "우아한형제들(배민)", "직방", "쏘카", "핀다", "카카오뱅크",
    "삼성SDS", "LG CNS", "SK C&C", "현대오토에버", "무신사", "야놀자",
    "NHN", "티맵모빌리티", "당근페이", "왓챠",
]

EXP_RANGES = {
    "junior": (1, 3),
    "mid": (4, 7),
    "senior": (8, 15),
}


def rand_exp(stage: str) -> int:
    lo, hi = EXP_RANGES[stage]
    return random.randint(lo, hi)


def _josa_로(word: str) -> str:
    """받침 유무에 따라 '으로'/'로' 조사를 붙인다 (괄호 등 특수문자는 무시)."""
    core = word.rstrip(")").rstrip("」").rstrip("'\"")
    if not core:
        return "로"
    last = core[-1]
    if "가" <= last <= "힣":
        return "으로" if (ord(last) - 0xAC00) % 28 != 0 else "로"
    return "로"


def build_background(school: str, major: str, company: str) -> str:
    tmpl = random.choice(CAREER_PATH_TEMPLATES)
    return tmpl.format(school=school, major=major, company=company, josa=_josa_로(company))


def build_spec(domain: str, role_name: str, company_pool: list[str],
                major_pool: list[str] = MAJORS_AI, stage: str | None = None) -> dict:
    school = random.choice(SCHOOLS)
    major = random.choice(major_pool)
    company = random.choice(company_pool)
    stage = stage or random.choices(
        ["junior", "mid", "senior"], weights=[0.35, 0.4, 0.25]
    )[0]
    exp = rand_exp(stage)
    role = f"{role_name}, {company}"
    background = build_background(school, major, company)
    return {"domain": domain, "role": role, "exp": exp, "background": background}


# ─────────────────────────────────────────
# 분포 정의: (domain, role_name_pool, count)
# ─────────────────────────────────────────

def with_non_tech_mix(major_pool: list[str], ratio: float = 0.15) -> list[str]:
    """비전공 전환 배경도 일부 섞기 위한 helper (매 호출 시 학과 목록 결정에 사용)"""
    return major_pool


AI_GROUPS = [
    ("데이터분석/AI - 머신러닝/딥러닝", [
        "머신러닝 엔지니어", "딥러닝 엔지니어", "AI 리서처", "ML 플랫폼 엔지니어",
    ], 20),
    ("데이터분석/AI - 컴퓨터비전", [
        "컴퓨터비전 엔지니어", "비전 AI 연구원", "이미지 인식 엔지니어",
    ], 10),
    ("데이터분석/AI - NLP/LLM", [
        "NLP 엔지니어", "LLM 엔지니어", "대화형 AI 연구원", "언어모델 리서처",
    ], 15),
    ("데이터분석/AI - MLOps/인프라", [
        "MLOps 엔지니어", "AI 인프라 엔지니어", "ML 플랫폼 SRE",
    ], 10),
    ("데이터분석/AI - 데이터사이언티스트", [
        "데이터 사이언티스트", "시니어 데이터 사이언티스트", "Applied Scientist",
    ], 15),
    ("데이터분석/AI - 데이터분석가", [
        "프로덕트 데이터 분석가", "마케팅 데이터 분석가", "금융 데이터 분석가",
        "커머스 데이터 분석가", "그로스 데이터 분석가", "BI 애널리스트",
    ], 25),
    ("데이터분석/AI - 데이터엔지니어", [
        "데이터 엔지니어", "데이터 플랫폼 엔지니어", "빅데이터 엔지니어",
    ], 15),
    ("데이터분석/AI - AI/데이터 PM", [
        "AI 프로덕트 매니저", "데이터 프로덕트 매니저", "AI 서비스 기획자",
    ], 10),
]

IT_GROUPS = [
    ("IT개발/백엔드", ["백엔드 엔지니어", "시니어 백엔드 엔지니어", "서버 개발자"], 10),
    ("IT개발/프론트엔드", ["프론트엔드 엔지니어", "웹 프론트엔드 개발자"], 5),
    ("IT개발/게임", ["게임 클라이언트 개발자", "게임 서버 개발자", "게임 PM"], 5),
    ("IT개발/QA", ["QA 엔지니어", "테스트 자동화 엔지니어"], 5),
    ("IT개발/클라우드", ["클라우드 인프라 엔지니어", "DevOps 엔지니어", "SRE"], 5),
    ("IT개발/PM", ["IT 프로덕트 매니저", "테크 PM", "서비스 기획 PM"], 10),
]

OTHER_GROUPS = [
    ("금융/투자", ["자산운용사 리서치 애널리스트", "IBD 어소시에이트", "PB", "VC 심사역"], 8),
    ("브랜드마케팅", ["브랜드 마케터", "콘텐츠 마케팅 매니저"], 6),
    ("퍼포먼스마케팅", ["퍼포먼스 마케터", "그로스 마케터"], 5),
    ("MD/유통", ["MD", "이커머스 MD", "리테일 바이어"], 5),
    ("전략기획/컨설팅", ["전략기획 매니저", "경영 컨설턴트", "BizDev 매니저"], 6),
    ("HR/인사", ["HRD 매니저", "채용 담당자", "People Ops 리드"], 5),
    ("UX/UI디자인", ["Product Designer", "UX 리서처"], 3),
    ("생산/품질/제조", ["생산관리 담당자", "품질관리 엔지니어"], 2),
]

OTHER_COMPANIES = [
    "삼성전자", "LG전자", "현대자동차", "SK하이닉스", "신한은행", "미래에셋자산운용",
    "나이키코리아", "아모레퍼시픽", "무신사", "SSG닷컴", "맥킨지", "딜로이트",
    "네이버", "카카오", "CJ제일제당", "아모레", "롯데", "이랜드",
]


def build_all_specs() -> list[dict]:
    specs: list[dict] = []
    for domain, role_pool, count in AI_GROUPS:
        for _ in range(count):
            role_name = random.choice(role_pool)
            major_pool = MAJORS_AI if random.random() > 0.15 else MAJORS_NON_TECH
            specs.append(build_spec(domain, role_name, AI_COMPANIES, major_pool))
    for domain, role_pool, count in IT_GROUPS:
        for _ in range(count):
            role_name = random.choice(role_pool)
            major_pool = MAJORS_AI if random.random() > 0.2 else MAJORS_NON_TECH
            specs.append(build_spec(domain, role_name, IT_COMPANIES, major_pool))
    for domain, role_pool, count in OTHER_GROUPS:
        for _ in range(count):
            role_name = random.choice(role_pool)
            specs.append(build_spec(domain, role_name, OTHER_COMPANIES, MAJORS_NON_TECH))
    random.shuffle(specs)
    return specs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="spec만 생성하고 LLM 호출/저장 없이 분포만 확인")
    args = parser.parse_args()

    specs = build_all_specs()
    print(f"총 spec 수: {len(specs)}")

    if args.dry_run:
        from collections import Counter
        domain_counts = Counter(s["domain"] for s in specs)
        report = {
            "total": len(specs),
            "domain_counts": dict(domain_counts.most_common()),
            "sample_specs": specs[:5],
        }
        report_path = ROOT / "data" / "cleaned" / "mentor_persona_v2_spec_check.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"dry-run 리포트 저장: {report_path}")
        return

    db = json.loads(MENTORS_DB.read_text(encoding="utf-8"))
    existing_count = len(db["records"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = MENTORS_DB.with_name(f"mentors.backup_{timestamp}.json")
    shutil.copy2(MENTORS_DB, backup_path)
    print(f"백업 완료: {backup_path}")

    records = []
    errors = []
    for i, spec in enumerate(specs, 1):
        try:
            rec = generate_mentor(spec)
            records.append(rec)
            if i % 10 == 0 or i == len(specs):
                print(f"  [{i:03d}/{len(specs)}] {rec['mentor_info'].get('name','?')} — {rec['current_role']}")
        except Exception as e:
            errors.append({"index": i, "spec": spec, "error": str(e)})
            print(f"  [{i:03d}] ERROR: {e}")

    db["records"].extend(records)
    MENTORS_DB.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "existing_count_before": existing_count,
        "generated_count": len(records),
        "error_count": len(errors),
        "errors": errors,
        "total_after": existing_count + len(records),
        "backup_path": str(backup_path),
    }
    report_path = ROOT / "data" / "cleaned" / "mentor_persona_v2_run_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
