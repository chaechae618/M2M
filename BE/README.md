# M2M Backend

M2M API 명세서 v1.1의 멘티 전용 로그인·AI 멘토 페르소나 구조를 구현하는 FastAPI 백엔드다.

## 현재 구현 범위

- FastAPI 애플리케이션과 `/health`, `/ready` 상태 확인
- 공통 성공·오류 응답
- SQLAlchemy DB 연결
- 멘티 회원가입·로그인·토큰 갱신·로그아웃·내 계정 조회
- 멘티 프로필·경험 CRUD와 이력서·포트폴리오 업로드
- 기존 `M2M-mentoring-agent`의 Agent 1 추가 질문·질문 정제 호출
- 기존 Agent 2의 자산 검색과 `llm_direct`·`mentor_needed` 라우팅 호출
- 기존 Agent 3와 250명 멘토 DB를 이용한 Top 3 추천
- 선택된 AI 멘토 페르소나 답변 Agent 호출
- 만족도, 재사용 동의·철회와 기존 Agent 4 자산화 호출
- 로그인 멘티 전용 Q&A 게시글·이미지·댓글 CRUD
- 인프로세스 백그라운드 작업과 작업 상태 조회

## 실행

Python 3.11 이상이 필요하다.

macOS에서 프로젝트용 Conda 환경을 사용하는 경우:

```bash
cd BE
conda create -n m2m-be python=3.11 -y
conda run -n m2m-be pip install -r requirements.txt
cp .env.example .env
# 실제 Agent를 사용할 때만 .env의 OPENAI_API_KEY에 키 설정
conda run --no-capture-output -n m2m-be python -m uvicorn app.main:app --reload
```

Windows PowerShell에서 venv를 사용하는 경우:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# 실제 Agent를 사용할 때만 .env의 OPENAI_API_KEY에 키 설정
python -m uvicorn app.main:app --reload
```

확인:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

## DB

로컬 기본값은 SQLite다. 공유 개발·운영 환경에서는 `.env`의 `DATABASE_URL`을 PostgreSQL로 변경한다.

```text
postgresql+psycopg://m2m:m2m@localhost:5432/m2m
```

개발 모드에서는 서버 시작 시 테이블을 생성한다. 첫 운영 배포 전 Alembic 마이그레이션을 확정해야 한다.

## Agent 연결 구조

핵심 판단과 프롬프트는 `../M2M-mentoring-agent`에만 둔다. FastAPI는
`app/services/mentoring_agent_adapter.py`를 통해 기존 Agent를 호출하고,
인증·HTTP 요청/응답·SQL 작업 상태만 관리한다.

```text
FastAPI → Agent 1 → Agent 2 → Agent 3 → 페르소나 답변 → Agent 4
```

`MENTORING_AGENT_MODE`는 `auto`, `live`, `demo`를 지원한다. 기본 `auto`는
`OPENAI_API_KEY`가 있으면 실제 Agent를, 없으면 전체 UI 흐름을 검증할 수 있는 로컬
데모 Agent를 사용한다. 운영에서는 `live`와 실제 키를 사용한다. 일반 `pytest`도
테스트 대역을 사용하므로 OpenAI를 호출하거나 비용을 발생시키지 않는다.

현재 비동기 작업은 FastAPI 프로세스 내부 백그라운드 작업이다. 운영 환경에서는
Celery, RQ 또는 Dramatiq와 같은 영속 Worker로 교체해야 한다.

## 구현 기준

- `../docs/M2M_API_명세서_v1.1_페르소나.md`
- `../docs/M2M_API_명세서_v1.0_v1.1_비교.md`
- `../docs/M2M_ERD_v1.1.md`
