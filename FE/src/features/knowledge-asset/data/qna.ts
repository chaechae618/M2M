export type QnaImagePosition = "top-left" | "top-center" | "top-right" | "bottom-left" | "bottom-center" | "bottom-right";

export type QnaArticle = {
  id: string;
  category: string;
  title: string;
  excerpt: string;
  mentor: string;
  age: string;
  scraps: number;
  saved: boolean;
  avatarColor: string;
  imagePosition: QnaImagePosition;
};

export const qnaArticles: QnaArticle[] = [
  {
    id: "pm-first-step",
    category: "기획 · PM",
    title: "비전공자인데 PM을 준비하려면 무엇부터 해야 할까요?",
    excerpt:
      "안녕하세요. 저는 지금 디자인 전공 중인데 요즘 PM 직무에 관심이 생겼어요. 주변에서는 PM 하려면 개발도 알아야 하고 데이터도 볼 줄 알아야 한다고 하는데, 어디까지 준비해야 하는지 잘 모르겠습니다. 개발을 깊게 공부해야 하는 건지, 아니면 서비스 기획이나 프로젝트 경험을 먼저 쌓는 게 나은 건지 궁금해요.",
    mentor: "프로덕트 매니저",
    age: "2일 전",
    scraps: 5,
    saved: true,
    avatarColor: "#cdd6d8",
    imagePosition: "bottom-center",
  },
  {
    id: "hr-data",
    category: "인사 · 총무 · 노무",
    title: "HR 실무에 필요한 데이터 역량이 궁금합니다",
    excerpt:
      "인사 업무도 감이나 커뮤니케이션뿐 아니라 데이터를 활용하는 능력이 중요하다고 들었습니다. 신입 지원자가 엑셀이나 HR 데이터 분석을 어느 수준까지 준비해야 하는지 알고 싶습니다.",
    mentor: "HR 조직문화",
    age: "2년 전",
    scraps: 10,
    saved: false,
    avatarColor: "#ffddb3",
    imagePosition: "top-center",
  },
  {
    id: "marketing-intern",
    category: "마케팅",
    title: "마케팅 인턴 지원 전에 어떤 경험을 만들어야 할까요?",
    excerpt:
      "마케팅 인턴을 지원해보고 싶은데 관련 경험이 거의 없어서 걱정입니다. 대외활동도 많이 안 했고, 포트폴리오에 넣을 만한 결과물도 별로 없어요. 지금부터라도 블로그나 인스타그램을 운영해보는 게 도움이 될까요?",
    mentor: "브랜드 마케터",
    age: "1달 전",
    scraps: 2,
    saved: true,
    avatarColor: "#f1bbbc",
    imagePosition: "top-right",
  },
  {
    id: "ai-marketer",
    category: "마케팅 · MD",
    title: "AI 시대, 마케터에게 필요한 진짜 역량",
    excerpt:
      "마케팅 직무를 준비하면서 콘텐츠 기획뿐 아니라 데이터 분석과 AI 도구 활용까지 공부하고 있습니다. 빠르게 변하는 환경에서 신입 마케터가 우선적으로 갖춰야 할 역량이 무엇인지 알고 싶습니다.",
    mentor: "콘텐츠 마케터",
    age: "1주일 전",
    scraps: 12,
    saved: false,
    avatarColor: "#bdd99b",
    imagePosition: "bottom-left",
  },
  {
    id: "ux-portfolio",
    category: "UXUI",
    title: "UX 포트폴리오에 화면 결과물만 넣어도 괜찮을까요?",
    excerpt:
      "UX 디자인 포트폴리오를 만들고 있는데 고민이 많아요. 지금까지는 앱 화면이나 웹 화면 위주로 정리했는데, 주변에서 과정이 중요하다고 해서 다시 고쳐야 하나 싶습니다.",
    mentor: "UXUI 디자이너",
    age: "5일 전",
    scraps: 0,
    saved: false,
    avatarColor: "#f9e2ae",
    imagePosition: "bottom-right",
  },
];

export const qnaDetail = {
  title: "비전공자인데 PM 준비하려면 뭐부터 해야 하나요?",
  age: "2일 전",
  views: "10,000",
  scraps: 0,
  body: [
    "안녕하세요. 저는 지금 디자인 전공 중인데 요즘 PM 직무에 관심이 생겼어요.",
    "서비스를 직접 만드는 일도 재밌어 보이고, 사용자 문제를 찾고 해결 방향을 정리하는 과정도 흥미로워서 PM 쪽을 알아보고 있습니다. 그런데 주변에서는 PM을 하려면 개발도 알아야 하고, 데이터도 볼 줄 알아야 하고, 커뮤니케이션도 잘해야 한다고 해서 어디서부터 시작해야 할지 모르겠어요.",
    "개발을 깊게 공부해야 하는 건지, 아니면 서비스 기획이나 프로젝트 경험을 먼저 쌓는 게 나은 건지도 헷갈립니다. 아직 실제로 출시한 서비스 경험은 없고, 학교 팀 프로젝트나 과제 정도만 해본 상태예요.",
    "비전공자가 PM을 준비할 때 가장 먼저 해야 할 일이 뭘까요? 포트폴리오에는 어떤 경험을 넣으면 좋을지도 궁금합니다.",
  ],
  answer:
    "개발 지식은 있으면 분명 도움이 되지만, 처음부터 개발자처럼 공부할 필요는 없어요.\n대신 개발자와 대화할 수 있을 정도의 기본 개념은 알아두면 좋아요.\n\n프론트엔드와 백엔드가 어떻게 나뉘는지, API가 뭔지, 데이터가 어디에 저장되고 어떻게 화면에 보여지는지 정도를 이해하면 협업할 때 훨씬 수월합니다. 그다음에는 서비스 분석, 사용자 인터뷰, 기능 우선순위 정리 같은 PM다운 경험을 쌓아보세요.",
};

export type RelatedArticle = {
  title: string;
  excerpt: string;
  scraps: number;
  imagePosition: QnaImagePosition;
};

export const relatedArticles: RelatedArticle[] = [
  {
    title: "PM 포트폴리오에 꼭 들어가야 하는 5가지",
    excerpt: "문제 정의, 사용자 리서치, 우선순위 판단, 화면 흐름, 개선 방향을 어떤 순서로 정리하면 좋은지 알려드려요.",
    scraps: 12,
    imagePosition: "top-left",
  },
  {
    title: "서비스 기획 경험이 부족할 때 만들 수 있는 사이드 프로젝트",
    excerpt: "실제 출시 경험이 없어도 사용자 문제를 발견하고 기획 과정으로 보여줄 수 있는 프로젝트 주제를 추천해요.",
    scraps: 0,
    imagePosition: "top-right",
  },
  {
    title: "비전공자가 PM 면접에서 자주 받는 질문",
    excerpt: "개발 지식이 부족할 때 어떻게 답하면 좋은지, 프로젝트 경험을 PM 역량으로 연결하는 방법을 정리했어요.",
    scraps: 2,
    imagePosition: "bottom-left",
  },
  {
    title: "SQLD 자격증과 PM 준비",
    excerpt: "데이터 기반으로 의사결정하는 PM이 되고 싶어서 SQLD 자격증을 준비해볼까 고민 중입니다.",
    scraps: 9,
    imagePosition: "bottom-right",
  },
];
