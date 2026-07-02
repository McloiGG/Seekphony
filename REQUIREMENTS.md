Week 4 : Independent Project

Independent System Build, Testing \& Deployment 

Objective - Collaborative Project with Another Peer

Up until this point, you have built individual system components:

Week 1 → Data pipeline (ETL)

Week 2 → AI decision-making module

Week 3 → Application layer (frontend + backend integration)

Week 4 is no longer an exercise in following instructions. It is a simulation of building a real-world system under constraints. In this module, you will move beyond guided implementation and:

define your own problem space

design a complete system architecture

build, test, and refine a full application

deploy and present a working solution

Core Philosophy

A working system is not defined by code alone. A strong system:

solves a clear and meaningful problem

uses data and AI intentionally (not for decoration)

integrates components cleanly

handles failure cases

can be explained, defended, and demonstrated

AI Usage Guidelines

AI can significantly help developers to increase productivity, especially for accelerating repetitive tasks, exploring ideas, and supporting implementation. However, it should be used deliberately with the following awareness: 

Use AI to assist with repetitive or time-consuming tasks.

Before using AI, take time to understand the problem you are trying to solve. Clear thinking leads to better prompts, and better prompts lead to more useful results.

Treat AI-generated code as starting points rather than final answers. Critically review AI output. Test it, question it, and ensure it aligns with your intended logic and requirements.

Blindly copying or “vibe coding” solutions without understanding will create gaps that become obvious during evaluation, leading to a low score or even failure.

Seek feedback from peers to validate your work. Discussing ideas, reviewing each other’s work, and challenging assumptions will often provide insights that AI alone cannot offer.

Your growth in this program depends on your ability to reason through problems, collaborate with peers, and build systems with intention. Use AI as a tool to enhance that process, not shortcut it.

General Instructions

Work in pairs

Create a new GitHub repository with a meaningful name.

All git commit messages must follow Conventional Commits v1.0.0

Format all Python code with ruff version 0.15.\*

Ensure you are running Python version 3.14.\*

Ensure you are using uv version 0.8.\*

All packages are allowed, but unused packages must be removed from pyproject.toml, with the exception of OS-specific packages of course.

Ensure all packages are pinned to exact versions to prevent breaking changes.

Do not expose API keys or secrets

You are free to incorporate additional technologies, frameworks, languages, or services where appropriate, provided the core project remains executable and evaluable by the programme facilitators. (Python is still mandatory)

You are free to choose your:

problem

dataset

system design

feature scope

However, your project must satisfy the following minimum requirements:

The project must solve a real and clearly defined problem

The project must include:

a data component

an AI component

a frontend/backend application

The system must process real input data

The AI component must perform a meaningful task beyond simple prompt-response interaction

The project must be realistically achievable within the programme timeframe

The final system must be:

functional

testable

demo-ready

Teams are strongly encouraged to prioritize:

reliability

usability

maintainability

scope control

Strong Recommendations

Avoid:

building generic chatbot clones

over-engineering infrastructure

excessive feature creep

choosing datasets that are too large or too complex to process within the timeframe

depending heavily on paid APIs or unstable services

A smaller but complete system is preferred over an ambitious but unfinished system.

Project Structure (Suggested)

week\_4/

├── data/                  # Data sources / processed data

├── backend/

│   ├── src/

│   └── week\_2/           # Reuse or adapt AI module

├── frontend/

│   └── src/

├── scripts/              # Optional utilities / pipelines

├── tests/                # Testing logic (optional but encouraged)

├── docker-compose.yml

├── .env.example

└── README.md

​

Timeline (Suggested)

Day

Focus

Day 1

• Clear problem statement

• Identified target users and use cases

• Selected dataset(s) or data sources

• Initial system architecture and component breakdown

• Defined MVP feature scope

• Explanation of where and why AI is used

• Validation of problem relevance and project feasibility

Day 2

• Working data ingestion/transformation component

• Functional AI component

• Database integration

• Frontend ↔ backend communication

• Initial end-to-end pipeline

• Modular architecture with structured AI outputs

• Validation and fallback handling

Day 3

• Error handling and edge case handling

• UI/UX refinement

• Environment variable handling

• Docker/Docker Compose setup (optional)

• Deployment preparation

• README improvements

• Awareness of hallucinations, invalid outputs, scalability, cost, and reliability concerns

Day 4

• Fully working integrated application

• Final README/documentation

• Architecture explanation

• Presentation/demo preparation

• Final testing and debugging

Final

Demo \& evaluation

• Problem and impact clearly communicated

• Core features functional end-to-end

• AI usage is meaningful and validated

• Clear separation of data, AI, and application layers

• Working frontend, backend, and integration flow

• Proper configuration and error handling

• Ability to explain architecture, AI logic, trade-offs, and limitations

• Awareness of deployment, privacy, cost, and scaling considerations



\# Mandatory Components



\## Your system must include \*\*all of the following\*\*:



\### 1. Data Component



\- ingestion, transformation, or external API usage

\- structured input → processed output

\- must be reusable and modular



\### 2. AI Component



\- meaningful use of LLM or model-based logic

\- not just raw prompt-response

\- must include:

&#x20;   - validation

&#x20;   - structured output

&#x20;   - fallback handling



\### 3. Application Layer



\- user interface (web-based)

\- backend API

\- interaction flow between user and system



\### 4. Integration Layer



\- environment variables handled properly

\- all modules must work together

\- clear separation of concerns:

&#x20;   - data logic

&#x20;   - AI logic

&#x20;   - application logic



\---



\## Functional Requirements



Your system must:



\- accept real user input

\- process input through your pipeline (data → AI → output)

\- return meaningful, structured results

\- handle invalid input and errors gracefully

\- be usable without reading your code



\## Non-Functional Requirements



Your system must demonstrate:



\- modular design

\- readability and maintainability

\- basic performance awareness

\- error handling and resilience

\- security awareness (no exposed secrets)



\# Example Project Themes



\### You are strongly encouraged to choose a \*\*clear problem domain\*\*. Below are suggested directions (not mandatory):



\## 1. Real-World Insight System (Data → AI → Decision)



\### Concept



Build a system that transforms messy real-world data into \*\*actionable insights for users\*\*.



\### Example Directions



\- Cost of living estimator (based on location + lifestyle)

\- Job market trend analyzer (skills demand, salary signals)

\- Public dataset explorer (health, transport, economy)



\### Focus



\- Data pipeline quality (Week 1)

\- AI interpretation layer (Week 2)

\- Clear output for user decisions (Week 3)



\### Common Pitfalls



\- dumping raw charts instead of insights

\- using AI to “summarize” instead of \*\*reason\*\*

\- no clear user decision outcome



\---



\## 2. Decision Support System (Structured Reasoning Engine)



\### Concept



Build a system that helps users make \*\*better decisions under constraints\*\*. This is not “advice.” This is \*\*structured reasoning backed by data and logic\*\*.



\### Example Directions



\- Budget planner with trade-off analysis

\- Career path simulator (skills vs market demand)

\- Study planner with time/resource constraints



\### Focus



\- combining:

&#x20;   - user input

&#x20;   - data sources

&#x20;   - AI reasoning

\- producing \*\*ranked or justified outputs\*\*

\- explain \*why\* a recommendation is made

\- handle multiple factors (not single-variable logic)



\### Common Pitfalls



\- producing generic suggestions

\- no reasoning trace

\- no real constraints in decision-making



\---



\## 3. Intelligent Workflow Automation System (AI as Core Logic)



\### Concept



Build a system that \*\*automates a real task\*\*, where AI is responsible for transforming input into structured, usable output.



\### Example Directions



\- Meeting notes → action items + task tracker

\- Documents → classification + recommendation system

\- Emails/messages → priority + response drafting



\### Focus



\- AI as a \*\*processing engine\*\*, not UI gimmick

\- structured outputs (JSON, validated results)

\- reliability (fallbacks, error handling)



\### Common Pitfalls



\- wrapping GPT in a UI and calling it a system

\- no validation or determinism

\- outputs that are not usable programmatically



\---



\## 4. Open Topic



Any idea is allowed if:



\- the problem is clearly defined

\- the system architecture is coherent

\- AI and data are used meaningfully

\- The project clearly demonstrates a full pipeline:



```

input → processing (data/AI) → structured output → user-facing result

```



\# Submission Guidelines



\## General submission guidelines



\*\*You need to create a new repository.\*\* Remember to push your work into your git repository. Only the work inside your git repository will be evaluated. Double-check file names. It is encouraged to submit before the cutoff period. Make sure your \*\*NEW\*\* git repository is \*\*publicly\*\* accessible!



\## 1. Working Application



\- fully functional system

\- runnable locally or deployed



\## 2. Git Repository



Must include:

\* clean project structure

\* meaningful commit history

\* no secrets or unnecessary files



\## 3. README.md



Must include:



\### Project Overview



\- problem statement

\- target users

\- system goal



\### System Architecture



\- data flow (input → processing → output)

\- module breakdown



\### Setup \& Installation



\- how to run the system

\- dependencies and environment setup



\### Features



\- list of implemented features

\- explanation of each



\### Technical Decisions



\- architecture choices

\- trade-offs made



\### Limitations



\- known issues

\- future improvements



\## 4. Demo Presentation (15 mins pitch, 15 mins QnA)



You are expected to prepare a pitching deck that does the following:

\* explain the problem → solution clearly

\* walk through the system flow

\* demonstrate key features

\* answer technical questions



\# Evaluation Rubric



Your project will be evaluated based on the following areas in \*\*15 minutes\*\*:



| Category | Weight |

| --- | --- |

| Problem \& Impact | 15% |

| Solution Quality | 20% |

| Innovation \& Creativity | 10% |

| Technical Implementation | 25% |

| Presentation \& Demo | 10% |

| Feasibility \& Realism | 5% |

| Technical Understanding | 15% |

| Bonus | +25% |



\---



\## 1. Problem \& Impact (15%)



We will evaluate:



\- Is the problem clearly defined?

\- Who are the intended users?

\- Is there evidence that the problem actually exists?

\- Is AI genuinely useful for solving the problem?



Strong projects solve a real problem for real users.



\---



\## 2. Solution Quality (20%)



We will evaluate:



\- Are the core features working?

\- Does the system function end-to-end?

\- Are AI outputs structured and usable?

\- Does the application provide a reasonable user experience?

\- Are common failure cases handled appropriately?



Strong projects are reliable and complete.



\---



\## 3. Innovation \& Creativity (10%)



We will evaluate:



\- Is the idea differentiated from common chatbot demos?

\- Does the project apply AI in a meaningful way?

\- Is there evidence of creative thinking in the workflow or solution design?



Strong projects demonstrate thoughtful problem solving.



\---



\## 4. Technical Implementation (25%)



We will evaluate:



\- Separation between Data, AI, and Application layers

\- Data ingestion and processing pipeline

\- AI validation and fallback handling

\- Frontend and backend integration

\- Environment variable handling

\- Error handling and resilience

\- Code quality and maintainability

\- Docker Compose orchestration



Strong projects demonstrate sound engineering practices.



\---



\## 5. Presentation \& Demo (10%)



We will evaluate:



\- Clarity of explanation

\- Ability to demonstrate the project successfully

\- Ability to explain architecture and technical decisions



Strong projects communicate ideas effectively.



\---



\## 6. Feasibility \& Realism (5%)



We will evaluate:



\- Whether the solution is realistic

\- Awareness of deployment challenges

\- Awareness of hallucinations, privacy, cost, and scalability concerns



Strong projects understand real-world constraints.



\---



\## 7. Technical Understanding (15%)



Every participant should be able to explain:



\- System flow from input to output

\- How the AI component works

\- Architectural decisions and trade-offs

\- Major implementation choices



Understanding your project is part of the evaluation.



Being unable to explain significant portions of your own code may negatively affect your score.



\---



\## Bonus Opportunities (+25%)



Additional credit may be awarded for:



\- CI/CD pipelines

\- RAG systems

\- Multi-step AI workflows

\- Multi-user functionality

\- Analytics dashboards

\- Monitoring and observability

\- Performance optimization

\- Caching strategies



Bonus features do not compensate for missing core requirements.



\# BONUS



\*NOTE: ensure that you have completed the mandatory parts before implementing any of the following:\*



\- CI/CD pipeline (GitHub Actions)

\- advanced AI pipelines (RAG, chaining)

\- analytics dashboard

\- multi-user support

\- performance optimization

\- system monitoring

# \*\*Week 4 Projects Further Clarification README\*\*



Following up on our earlier overview of the Week 4 Challenge, we would like to clarify further regarding your project evaluation, and the Showcase Day event!



🎓 \*\*Week 4 Evaluation (3rd July 2026)\*\*

As you head into the Week 4 evaluation session, you will no longer be evaluating each other:-



\- \*\*Technical Evaluation: \*\*Your final codebase, data architecture, and application layer will be evaluated directly by the 42 Malaysia Technical Staff. 



\- \*\*Facilitator Support: \*\* After evaluation with the 42 Malaysia Technical Staff, you will then join your facilitator to discuss the feedback and evaluation. 



\- \*\*1 hour evaluation:\*\* 30 minutes with 42 Malaysia Technical Staff \& 30 minutes with Facilitator



\# 🌟 \*\*The Ultimate Destination: July 10th Showcase Day\*\*

Your Week 4 project is \*\*not just an internal submission—it will serve as your official showcase piece for the Project Showcase Day on 10th July 2026.\*\*



This is your stage to pitch your solution, explain your architectural decisions, and run live product demonstrations. The audience in attendance will include key industry stakeholders, including:



\- Representatives from Khazanah Nasional

\- Government-Linked Companies (GLCs) \& Tech Startups

\- University Partners \& Sunway representatives



\- The Tentative Invite List of Companies to the Showcase Day is as attached. (You may assume that these are your audience) 



\*\*💡 Important Design Note:\*\* Because you are presenting to ecosystem leaders and potential employers, ensure the outcome of your project focuses on a real-world problem you observe that genuinely needs a digital solution. Treat this week with the intensity, focus, and professionalism of a true hackathon!

# FAQ:
Can I work alone?
- No. Week 4 projects must be completed in pairs.
Can we have a team of 3?
- No. Teams consist of exactly 2 participants.
Do I need to continue my Week 1–3 project?
- No. You may reuse parts of previous weeks if useful, but Week 4 is a new project
with its own problem statement and scope.
Can we change project ideas halfway?
- Yes, but be realistic. Large scope changes late in the week usually result in
incomplete projects.
How difficult should the project be?
- Choose something that can realistically be completed, tested, and
demonstrated within the available timeframe.
Project Requirements
Can we build anything we want?
- Yes, provided the project satisfies the minimum requirements.
What are the mandatory components?
- Your project must contain:
o A Data Component
o An AI Component
o A Frontend Application
o A Backend Application
All components must work together as a complete system.
What is a Data Component?
- A component that collects, processes, transforms, stores, or analyzes data.
- Examples:
o ETL pipelines
o CSV processing
o Database systems
o API integrations
o Data cleaning pipelines
What is an AI Component?
A component that uses an AI model to perform a meaningful task.
- Examples:
o Classification
o Recommendation
o Summarization
o Information extraction
o Matching
o Decision support
What is NOT considered an AI Component?
Using AI only for decoration or novelty.
- Examples:
o Random chatbot unrelated to the problem
o AI-generated greetings
o AI responses that are never used by the system
o Technology Choices
Is Python mandatory?
- Yes.
- The project requires:
o Python 3.14
o uv
o ruff
The primary implementation language is Python.
Can I use React?
- Yes.
Can I use JavaScript?
- Yes
Can I use TypeScript?
- Yes.
Can I use Docker?
- Yes.
Can I use additional programming languages?
- Yes, but Python must remain part of the project and evaluators must still be able
to run and evaluate the system.
Can I use OpenAI instead of Gemini?
- Yes.
Can I use Claude?
- Yes.
Can I use local LLMs?
- Yes.
Can I use paid APIs?
- Yes, but be mindful of costs and reliability.
Data Questions
Do I need a dataset?
- Yes.
The project must process real input data.
Can I use APIs instead of datasets?
- Yes.
Can I use CSV files?
- Yes.
Can I scrape websites?
- Yes, provided you comply with the website's terms of service.
Can I generate fake data?
- Synthetic data may be used for testing, but your project should demonstrate
realistic usage.
Do I need a database?
- Not necessarily, but many projects will benefit from one.
AI Questions
Is AI mandatory?
- Yes.
Can I just build a chatbot?
- No.
- Generic chatbot clones are discouraged and will generally score poorly.
What counts as meaningful AI usage?
- The AI should directly help solve the problem being addressed.
Do I need RAG?
- No.
- RAG is optional and should only be used if it genuinely improves the solution.
Do I need agents?
- No.
Do I need fine-tuning?
- No.
Can I use prompt engineering only?
- Yes, if it produces meaningful outcomes and integrates properly into the system.
Frontend / Backend Questions
Do I need a frontend?
- Yes.
Do I need a backend?
- Yes.
Can my frontend be simple?
- Yes.
- A simple interface with good functionality is preferable to a complex interface
that does not work.
Can I make a CLI application?
- No.
- A frontend and backend application are required.
Deployment & Docker
Is Docker mandatory?
- No.
- Docker is recommended but not required.
Is deployment mandatory?
- No.
Will deployment help my evaluation?
- Yes.
A deployed and accessible project demonstrates additional effort and maturity.
- Evaluation
What matters more: idea or implementation?
- Implementation.
- A simple idea executed well usually scores higher than an ambitious idea
executed poorly.
What matters more: features or quality?
- Quality.
Can we pass with a simple project?
- Yes.
Can we fail with a complicated project?
- Yes.
- Complexity does not guarantee marks.
What if our demo breaks?
- Evaluators will consider the overall project, but a failed demo will impact your
score.
What if some features are unfinished?
- You can still present them, but incomplete functionality will not receive full
credit.
AI Usage During Development
Can I use ChatGPT to write code?
- Yes.
Can I use Cursor?
- Yes.
Can I use GitHub Copilot?
- Yes.
Do I need to disclose AI usage?
- Yes.
What if I used AI heavily?
- That is acceptable if you understand the code and can explain it.
What if I cannot explain my own code?
- Expect significant mark deductions and possible failure during technical
questioning.
