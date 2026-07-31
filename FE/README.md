# M2M Frontend

M2M 멘티 웹서비스의 Next.js 프론트엔드다. 브라우저는 Next.js Route Handler를
통해 FastAPI에 접근하며, 액세스 토큰과 리프레시 토큰은 HttpOnly 쿠키에 저장한다.

## 실행

```bash
cd FE
npm install
cp .env.example .env.local
npm run dev
```

백엔드는 기본적으로 `http://127.0.0.1:8000`에서 실행되어야 한다. 다른 주소를
사용할 때는 `.env.local`의 `BACKEND_URL`을 변경한다.

```text
http://localhost:3000
```

## 현재 API 연동

- 이메일 기반 회원가입·로그인·로그아웃과 토큰 자동 갱신
- 멘티 이름·현재 상태·관심 분야 수정
- 이력서 PDF/DOCX와 포트폴리오 PDF/PPTX 업로드·다운로드
- Q&A 목록·검색·상세·댓글 작성
- 상담 생성, 추가 대화, 질문 수정·확정, AI 멘토 선택과 답변 조회

멘토 회원가입 탭은 디자인에 남아 있지만 비활성화되어 있다. Q&A 스크랩과 프로필
이미지 수정은 백엔드 API가 추가된 뒤 연결한다. 실제 상담 Agent 실행에는 백엔드
`.env`의 `OPENAI_API_KEY`가 필요하다.

## 검증

```bash
npm run lint
npm run build
```
