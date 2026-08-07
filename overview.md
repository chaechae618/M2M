# Mentu-Men (Mentor to Menti, Man to Man)

**Track**: Domestic AI Track
**Team**: Chwijeongsa (5 members)
**Team Lead**: Lee Dong-heon (Dept. of Data Science, Psychology & Brain Science concentration, Hanyang University)

---

## 1. Background and Purpose

### 1.1 Motivation Behind the Idea

The hiring market has rapidly shifted from open, standardized recruitment to role-based, rolling recruitment. Companies now select candidates based on their understanding of the specific job and relevant practical experience, rather than average academic credentials. In this shift, applicants are increasingly expected to understand, on their own, what a given job actually entails and how to prepare for it — yet many young job seekers begin preparing without any clear standard for doing so.

**Supporting Data**
- According to a 2021 JobKorea survey, **46.9% of college students** had not yet decided on a career path.
- One of the key factors behind this indecision is cited as **a lack of job-related information and uncertainty about how to prepare**.

**The Structural Problem of Information Access**

Job-related information is often difficult to fully grasp from job postings alone; information about actual day-to-day work and how to prepare for it tends to rely heavily on the experiences of people already working in the field. However, access to this kind of information varies significantly depending on an individual's personal network, which creates a **structural information gap** in understanding a given job.

In this situation, young people try to obtain information through coffee chats or mentoring, but in practice run into two barriers:
1. **The "Who" problem**: it's hard to know who actually holds the information they need.
2. **The "What" problem**: they approach these conversations without a clear sense of what to ask.

As a result, people either repeat unproductive searches without getting sufficient information, or end up in inefficient interactions. In other words, this is not simply a problem of "there being no mentors" — it stems from **inefficiency in the search structure itself**.

### 1.2 Core Summary of the Idea

Mentu-Men converts a user's vague career concerns into concrete questions, and provides context-appropriate answers either through accumulated mentor knowledge assets or by connecting the user with an industry professional. All answers are turned into assets with consent, and are reused for future users.

**Before — The Existing Flow and Its Problems**

| Step | Description |
|---|---|
| ① Vague job-search preparation | "I don't know what I need to prepare." |
| ② Off-target questions | Approaching a professional without direction |
| ③ Inefficient conversation | Failing to get the information wanted |
| ④ Failed information search | Repeated searching · trial and error |

**Our Service — The Flow Mentu-Men Creates**

| Step | Description |
|---|---|
| ① Vague job-search preparation | "I don't know what I need to prepare." (same starting point) |
| ② AI-driven question refinement | Pinpointing exactly what the user wants to know |
| ③ Efficient question delivery | Gatekeeper decision routes to a direct answer or a mentor connection |
| ④ Accurate answer delivery | Immediate information provided · appropriate mentor connected |

The key point is that while the user's **starting point (vagueness) is the same**, from that point on AI steps in to refine the question and guide the user down the optimal path (an AI answer vs. a mentor connection).

### 1.3 The Problem the Idea Aims to Solve

Mentu-Men defines four structural difficulties that arise in the process of exploring careers and jobs, and aims to solve them.

- **Limited access to industry professionals**
  In a structure that relies on personal networks, the very opportunity to talk with an industry professional is limited if one lacks connections.

- **Difficulty identifying a suitable mentor**
  Even when a connection opportunity is available, there is no criterion for finding a professional who holds the information relevant to one's specific situation, given how varied job functions, industries, and career paths can be.

- **Lack of question-design skill**
  Many users start a conversation without having organized their situation into a concrete question, which results in not getting the information they wanted. This is a burden not only for the mentee, but also for the **mentor**, who receives a question with no context. The more a question is refined beforehand, the more a mentor can focus purely on giving a substantive answer — making this a two-sided problem.

- **Loss of experience over time**
  Even though similar questions recur repeatedly, the questions and answers remain unstructured and are never reused. The structural inefficiency in which individual experience fails to accumulate as a shared social asset keeps repeating.

**In summary**, these problems are not isolated from one another:
- It's hard to know who to ask (accessibility)
- It's unclear what to ask (question design)
- The results are never accumulated (lack of asset-building)

These three issues are intertwined and stem from the **limitations of the information-search structure itself**. In other words, the problem Mentu-Men defines is not simply "a lack of information," but rather **the structure's failure to effectively deliver the right information**.

---

## 2. Idea Details and Differentiation

### 2.1 Key Features and Scenario

Mentu-Men has a four-step structure in which a user's concern is refined into a conversational format, after which AI determines whether it can answer directly, and — if necessary — expands into a mentor connection.

**STEP 1 | Entering the Service**
The user enters the service without concrete information such as search keywords or specific job details.
> Example persona: "I'm curious about data-related jobs, but I don't know what I need to prepare." — a 4th-year sociology student

**STEP 2 | Question Refinement**
AI asks the first question, and the user answers — refining the vague concern through this back-and-forth. Rather than the user having to draft a well-formed question on their own, **the conversational structure itself, with AI actively asking follow-up questions, is what narrows things down**.
> Example: an input of "a vague data-related job" → AI reframes it into a more specific sub-question such as "In marketing, what level of SQL is typically required?"

**STEP 3 | Answer Branching**
- During the multi-turn conversation, the AI determines whether the question falls within a range it can answer on its own, or whether a mentor connection is needed.
- If a mentor connection is judged necessary, the **most suitable mentor is recommended** for that question.
- When the question is passed on to the mentor, it is not the user's original vague wording but rather a **structured, formalized version of the question** — reducing the burden of answering for the mentor.

**STEP 4 | The Information Circulation Structure**
- When both the mentor and the questioner **consent**, the mentoring answer is refined, tagged, and stored as an accumulated asset.
- The stored answer is later reused as supporting grounding for AI answers to similar future questions, or registered as Q&A board content.
> Example of an asset form: "A level of hands-on SQL data extraction is required" → accumulated as grounding for subsequent LLM answers / registered on the Q&A board

These four steps are not a one-off interaction; they are designed so that **accumulated answers circulate and benefit future users** — meaning the more people use the service, the better the overall answer quality of the system becomes.

### 2.2 Creativity and Differentiation

While existing services have focused solely on the single function of "connecting" people, Mentu-Men is fundamentally different in that it solves the problem through a circular structure of **judgment → connection → asset-building**.

- **Question design**
  Refines a vague concern into a question that supports decision-making, increasing the efficiency of the conversation. Users don't need to craft a good question themselves — the process of conversing with the AI is itself the process of refining the question.

- **Gatekeeper judgment**
  Rather than forwarding every question to a mentor, the system automatically branches between an LLM's own response and a mentor connection. This means mentors only need to respond to "questions the AI judged it could not answer, and that genuinely required a person" — greatly reducing mentor burden.

- **Asset-building**
  As answers accumulate on a consent basis, the quality of the AI's responses improves over time, while reliance on mentors gradually decreases. In other words, mentor dependency is high in the early stages of the service, but as usage accumulates, the range of questions the AI can handle on its own expands.

These three elements are not independent features but are designed as a **circular structure that reinforces each other's performance** (the better a question is designed → the more accurate the gatekeeper's judgment becomes → the more good answers accumulate → the richer the grounding becomes for designing the next question).

**Comparison Against Competing Service Types**

| Comparison Criterion | Existing Mentoring Platforms | Q&A Board–Type Services | General-Purpose LLM | Mentu-Men |
|---|---|---|---|---|
| Question refinement | X — vague question passed through as-is | X — depends on the author's own effort | X — surface-level question, surface-level answer | O — refined by a conversational agent |
| Question branching | X — every question goes to a mentor | X — no clarity on who will answer | X — no path to connect with a mentor | O — automatically branched by the agent |
| Answer asset-building | X — evaporates after a 1:1 conversation | △ — lacks refinement, tagging, or searchability | X — disappears once the session ends | O — answers can be turned into assets with consent |
| Reducing mentor burden | X — must repeatedly answer the same questions | △ — no enforcement to actually answer | X — no mentor exists in the first place | O — mentor is only invoked when truly needed |

The core positioning this comparison highlights is that Mentu-Men is not "just a connection service," but rather **a circular information infrastructure that refines questions, connects people only where truly needed, and preserves the results as a reusable asset.**
