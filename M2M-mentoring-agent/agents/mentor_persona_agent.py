"""
에이전트 3.5: 멘토 페르소나 답변 에이전트

[역할]
Agent 3(멘토 매칭)이 추천한 멘토 중 멘티가 선택한 1명에 대해,
mentors.json에 저장된 페르소나 프로필(이름·배경·현재 직무·경력·자기소개)을
근거로 LLM이 해당 멘토인 것처럼 1인칭 답변을 생성한다.

실제 멘토 풀이 아직 없는 프로토타입 단계에서, CLI로 사람이 멘토인 척
답변을 타이핑하던 부분(main.py STEP 4)을 대체하기 위한 용도.

[에이전트 루프]
관찰: mentors.json에서 mentor_id로 페르소나 프로필 로드
행동: 페르소나 프로필 + 멘티 정제 질문/맥락 + Agent3 추천 이유를 근거로
      답변 본문(answer_content) + 한 줄 요약(answer_summarize) 동시 생성
검증: 길이 미달(150자 미만) 시 최대 2회 재생성 → 계속 실패하면 None 반환
      (호출부인 main.py에서 실패 시 기존 수동 입력 방식으로 폴백)

핵심 설계 원칙
- 프로필(matching_summary_text·현재 직무·경력)에 없는 회사 내부 정보,
  구체적 수치(연봉 등), 특정 채용 공고는 지어내지 않는다.
- 합격 보장·확정적 성공 여부는 단정하지 않는다 (다른 에이전트들과 동일한 원칙).
- 자산화 에이전트(Agent 4)의 입력 스펙(answer_content, answer_summarize)에
  그대로 맞춰서 반환한다.
"""

import os
import json
from openai import OpenAI
from db.json_db import get_mentor
from utils.env import load_project_env

load_project_env()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ─────────────────────────────────────────
# 프롬프트
# ─────────────────────────────────────────

PERSONA_ANSWER_PROMPT = """[Role]
너는 맨투맨(M2M) 진로 멘토링 서비스에서 아래 [멘토 프로필]을 가진 실제 현직자 멘토다.
이 멘토의 입장에서, 아래 [멘티 정보]에 담긴 질문에 1인칭으로 답변한다.

[멘토 프로필]
이름: {mentor_name}
현재 직무: {current_role}
경력: {years_of_experience}년
출신 학교/전공: {school} {major}
자기소개: {matching_summary_text}
이 멘토가 적합한 멘티 유형: {be_go}

[이 멘토가 추천된 이유 — Agent 3가 매칭 시 판단한 근거]
{recommendation_reason}

[멘티 정보]
정제된 질문: {refined_question}
멘티 맥락: {context}
현재 병목(current_bottleneck): {current_bottleneck}
기대 답변 유형(expected_answer_type): {expected_answer_type}
직무 전환 연결 가설(bridge_hypothesis): {bridge_hypothesis}
전이 가능 역량(transferable_skills): {transferable_skills}
세부 질문 단위(question_units): {question_units}

[답변 원칙]
- 위 [멘토 프로필]에 없는 회사 내부 정보, 구체적 수치(연봉·합격률 등), 특정 채용 공고 내용은 지어내지 않는다.
- 자기소개(matching_summary_text)의 배경과 톤을 살려 1인칭으로, 실제 현직자가 답하듯 자연스럽게 쓴다.
- [이 멘토가 추천된 이유]에 나온 경험이 자연스럽게 이어지면 답변 도입부에 살짝 녹여도 좋다. 억지로 언급하지는 않는다.
- current_bottleneck과 expected_answer_type을 답변의 핵심 방향으로 삼는다.
- bridge_hypothesis가 있는 경우(직무 전환 질문), 그 연결 논리를 검증·보완하는 관점으로 답한다.
- 실행 가능한 조언을 2~3개 포함한다.
- 합격 보장, 확정적 성공/이직 가능성은 단정하지 않는다. 멘토 개인 경험 기반의 조언임을 유지한다.
- 개인정보(실명 외 학번·연락처·특정 팀명 등)는 포함하지 않는다.
- 답변은 400~700자 내외의 자연스러운 문단으로 작성한다 (지나치게 딱딱한 번호 리스트보다 대화체 위주, 필요하면 짧은 열거는 가능).

[출력 형식] JSON만 출력한다.
{{
  "answer_content": "멘토 1인칭 답변 본문 (최소 400자)",
  "answer_summarize": "이 답변을 한 줄로 요약 (추후 다른 멘티에게 자산으로 검색될 때 쓰임)"
}}"""


# ─────────────────────────────────────────
# 에이전트 클래스
# ─────────────────────────────────────────

class MentorPersonaAgent:
    MODEL = "gpt-4.1-mini"
    MIN_LENGTH = 150   # Agent 4(AssetizeAgent)의 최소 길이 게이트와 동일 기준
    MAX_RETRIES = 2

    def run(
        self,
        mentor_id: str,
        refined_question: str,
        context: str = "",
        current_bottleneck: str = "",
        expected_answer_type: str = "",
        bridge_hypothesis: str = "",
        transferable_skills: list[str] | None = None,
        question_units: list[dict] | None = None,
        recommendation_reason: str = "",
    ) -> dict | None:
        print("[멘토 페르소나 답변 에이전트] 실행 중...")

        mentor = get_mentor(mentor_id)
        if not mentor:
            print(f"  관찰 | mentor_id={mentor_id} 프로필을 찾을 수 없음 → 생성 불가")
            return None

        mentor_info = mentor.get("mentor_info", {}) or {}
        background  = mentor.get("background", {}) or {}
        mentor_name = mentor_info.get("name", "멘토")

        units_text = (
            "; ".join(
                u.get("question", "") for u in (question_units or [])
                if isinstance(u, dict) and u.get("question")
            )
            or "없음"
        )
        transferable_text = ", ".join(transferable_skills or []) or "없음"

        prompt = PERSONA_ANSWER_PROMPT.format(
            mentor_name=mentor_name,
            current_role=mentor.get("current_role", ""),
            years_of_experience=mentor.get("years_of_experience", 0),
            school=background.get("school", ""),
            major=background.get("major", ""),
            matching_summary_text=mentor.get("matching_summary_text", ""),
            be_go=mentor.get("be_go", ""),
            recommendation_reason=recommendation_reason or "없음",
            refined_question=refined_question,
            context=context or "없음",
            current_bottleneck=current_bottleneck or "없음",
            expected_answer_type=expected_answer_type or "없음",
            bridge_hypothesis=bridge_hypothesis or "없음",
            transferable_skills=transferable_text,
            question_units=units_text,
        )

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(
                    model=self.MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.6 if attempt == 1 else 0.4,
                )
                result = json.loads(response.choices[0].message.content)
            except Exception as e:
                print(f"  답변 생성 실패 ({attempt}회차): {e}")
                continue

            answer_content   = (result.get("answer_content") or "").strip()
            answer_summarize = (result.get("answer_summarize") or "").strip()

            if len(answer_content) < self.MIN_LENGTH:
                print(
                    f"  검증 | 길이 미달 ({len(answer_content)}자 < {self.MIN_LENGTH}자) "
                    f"→ {'재생성' if attempt < self.MAX_RETRIES else '생성 실패 처리'} ({attempt}회차)"
                )
                continue

            if not answer_summarize:
                answer_summarize = answer_content[:100]

            print(f"  판단 | '{mentor_name}' 페르소나 답변 생성 완료 ({len(answer_content)}자)")
            return {
                "mentor_id":         mentor_id,
                "mentor_name":       mentor_name,
                "answer_content":    answer_content,
                "answer_summarize":  answer_summarize,
            }

        print("  → 페르소나 답변 생성 최종 실패 (호출부에서 수동 입력으로 폴백 필요)")
        return None
