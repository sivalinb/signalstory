from __future__ import annotations

import html
import json
import os
from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from signalstory import animation, labs, tutor
from signalstory.cards import milestone
from signalstory.course import ROOT, concepts, course, mission, missions, sources_for
from signalstory.progress import Progress
from signalstory.prom.data import EVALUATION_TIMES
from signalstory.prom.engine import query_rows, sql_query, start_local_engine

load_dotenv(ROOT / ".env", override=False)
st.set_page_config(page_title="SignalStory · Visual observability", page_icon="◈", layout="wide")
st.html("<style>" + (ROOT / "signalstory/style.css").read_text() + "</style>")


@st.cache_resource
def service(path):
    start_local_engine()
    return Progress(path or None)


store = service(os.getenv("SIGNALSTORY_DB", ""))
COURSE = course()
MISSIONS = missions()
CONCEPTS = concepts()
if "profile" not in st.session_state:
    st.session_state.profile, st.session_state.token = store.create()
    requested = st.query_params.get("mission", "")
    st.session_state.nav = "Mission" if requested in {m["id"] for m in MISSIONS} else "Start"
    st.session_state.current = requested if requested in {m["id"] for m in MISSIONS} else MISSIONS[0]["id"]
saved = animation.browser_profile(
    st.session_state.token, st.session_state.get("reset_profile_storage", False)
)
if saved and saved != st.session_state.token:
    found = store.resume(saved)
    if found:
        st.session_state.profile = found
        st.session_state.token = saved
        st.session_state.pop("last_answer", None)
    else:
        st.session_state.reset_profile_storage = True
        st.rerun()
learner = st.session_state.profile
summary = store.summary(learner)


def go_to(page, identity=None):
    st.session_state.nav = page
    if identity:
        st.session_state.current = identity
        st.query_params["mission"] = identity


def eyebrow(text):
    st.markdown(f'<div class="eyebrow">{html.escape(text)}</div>', unsafe_allow_html=True)


def heading(title, description):
    st.title(title)
    st.markdown(f'<p class="subtitle">{html.escape(description)}</p>', unsafe_allow_html=True)


def tip(label, body):
    st.markdown(
        f'<div class="tip"><div class="label">{html.escape(label)}</div><p>{html.escape(body)}</p></div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-icon">◈</span>SignalStory</div><div class="brand-caption">SEE IT. MAKE SENSE OF IT.</div>',
        unsafe_allow_html=True,
    )
    st.radio(
        "Your workspace",
        ["Start", "Journey", "Mission", "Review", "Ask a question", "My evidence", "Word guide"],
        key="nav",
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("YOUR LEARNING JOURNEY")
    st.progress(len(summary["done"]) / len(MISSIONS))
    st.caption(f"{len(summary['done'])} / 22 missions · {summary['xp']} XP")
    st.selectbox(
        "Choose a mission",
        [m["id"] for m in MISSIONS],
        key="current",
        format_func=lambda ident: (
            f"{'✓' if ident in summary['done'] else '○'} {MISSIONS.index(mission(ident)) + 1:02d} · {mission(ident)['title']}"
        ),
    )
    st.caption(f"{len(summary['due'])} concepts ready to revisit")
    with st.expander("Save or resume progress"):
        st.caption(
            "Your browser remembers this profile on this server. Keep a private recovery code as a backup."
        )
        st.download_button(
            "Save my recovery code",
            st.session_state.token,
            file_name="signalstory-private-recovery.txt",
            mime="text/plain",
        )
        with st.form("resume"):
            token = st.text_input("Private recovery code", type="password")
            resume = st.form_submit_button("Resume my journey")
        if resume:
            found = store.resume(token)
            if found:
                st.session_state.profile = found
                st.session_state.token = token.strip()
                st.session_state.reset_profile_storage = True
                for key in list(st.session_state):
                    if key == "last_answer" or key.startswith(
                        ("result-", "prediction-", "predictchoice-", "reflection-", "review-result-")
                    ):
                        del st.session_state[key]
                st.rerun()
            else:
                st.error("This server could not find that recovery code.")
    st.caption("Learn at your pace. Every lesson is open to preview.")


def draw_prom(result, key):
    rows = query_rows(result)
    if not rows:
        st.info("The result is empty. No matching evidence is different from a measured zero.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df.drop(columns=["timestamp"], errors="ignore"), hide_index=True, width="stretch", key=key)
    st.caption("Each row names a series. Its labels identify the measurement; value is the query result.")


def draw_sdk(data, key):
    if "before" in data:
        before, after = st.tabs(["Before response", "After response"])
        with before:
            draw_sdk(data["before"], key + "before")
        with after:
            draw_sdk(data["after"], key + "after")
        return
    a, b, c = st.columns(3)
    a.metric("Recorded spans", len(data["spans"]))
    b.metric("Correlated logs", len(data["logs"]))
    c.metric("Attempted requests", data["requests"])
    if data["spans"]:
        spans = pd.DataFrame(data["spans"])
        base = int(spans.start_ns.min())
        spans["start_ms"] = (spans.start_ns - base) / 1e6
        spans["operation"] = spans.service + " · " + spans.name + " · " + spans.span_id.str[-4:]
        colors = ["#b25745" if s == "ERROR" else "#147d71" for s in spans.status]
        fig = go.Figure(
            go.Bar(
                x=spans.duration_ms,
                y=spans.operation,
                base=spans.start_ms,
                orientation="h",
                marker_color=colors,
                customdata=spans[["trace_id", "parent_id", "status"]],
                hovertemplate="%{y}<br>Start %{base:.3f}ms · Duration %{x:.3f}ms<br>Status %{customdata[2]}<extra></extra>",
            )
        )
        fig.update_layout(
            height=min(620, 180 + len(spans) * 23),
            margin=dict(l=0, r=0, t=10, b=10),
            xaxis_title="Milliseconds from the first recorded span",
            yaxis=dict(autorange="reversed"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#264b4b",
        )
        st.plotly_chart(fig, width="stretch", key=key + "trace")
    st.caption(
        "Actual SDK timestamps from logical services in one Python process. This small workload is a teaching experiment, not a latency benchmark."
    )
    signals, logs_tab, context = st.tabs(["Metrics", "Logs", "Context"])
    with signals:
        st.json(data["metrics"], expanded=2)
    with logs_tab:
        st.json(data["logs"], expanded=1)
    with context:
        st.json(data["carriers"], expanded=1)
    if "collector" in data:
        st.caption(
            "Generated Collector configuration. Run the separate HTTP example to export actual OTLP data."
        )
        st.json(data["collector"], expanded=2)


def plan_controls(m, prefix, challenge=False):
    if m["kind"] == "promql":
        return st.text_area(
            "Your PromQL expression",
            "" if challenge else m["lab"]["starter"],
            height=120,
            key=prefix + "query",
            placeholder="Write an expression that satisfies the mission goal…",
        )
    plan = {}
    for field in m["lab"]["fields"]:
        name, label, kind = field["name"], field["label"], field["type"]
        if kind == "bool":
            plan[name] = st.checkbox(label, value=field["default"], key=prefix + name)
        elif kind == "int":
            plan[name] = st.number_input(
                label,
                min_value=int(field["minimum"]),
                max_value=int(field["maximum"]),
                value=int(field["default"]),
                step=1,
                key=prefix + name,
            )
        elif kind == "float":
            plan[name] = st.number_input(
                label,
                min_value=float(field["minimum"]),
                max_value=float(field["maximum"]),
                value=float(field["default"]),
                step=0.1,
                key=prefix + name,
            )
        elif field.get("options"):
            plan[name] = st.selectbox(
                label, field["options"], index=field["options"].index(field["default"]), key=prefix + name
            )
        else:
            plan[name] = st.text_input(label, field["default"], max_chars=100, key=prefix + name)
    return plan


def experiment(m):
    st.markdown("### Turn an idea into evidence")
    st.write(m["lab"]["goal"])
    scenario = st.radio(
        "Scenario", ["Normal traffic", "Incident"], horizontal=True, key="scenario-" + m["id"]
    )
    variant = 0 if scenario == "Normal traffic" else 1
    with st.form("experiment-" + m["id"]):
        plan = plan_controls(m, "exp-" + m["id"])
        run = st.form_submit_button("Run the experiment ↗", type="primary")
    if run:
        try:
            with st.spinner("Collecting evidence…"):
                result = labs.run(m, plan, variant)
            st.session_state["lab-" + m["id"]] = {"result": result, "variant": variant, "plan": plan}
            store.event(learner, "lab_run", m["id"])
        except (ValueError, RuntimeError, TypeError, KeyError) as exc:
            st.error(str(exc))
    saved_result = st.session_state.get("lab-" + m["id"])
    if saved_result and saved_result["variant"] == variant:
        result = saved_result["result"]
        if m["kind"] == "promql":
            draw_prom(result["data"], "prom-" + m["id"])
        else:
            draw_sdk(result["data"], "sdk-" + m["id"])
        st.download_button(
            "Save this experiment’s evidence",
            json.dumps(result, indent=2, default=str),
            file_name=m["id"] + "-evidence.json",
            mime="application/json",
        )
    with st.expander("A hint, when you need one"):
        st.write(m["lab"].get("hint") or "\n\n".join(m["lab"]["hints"]))
    if m["kind"] == "promql":
        with st.expander("Connect the idea to SQL"):
            st.write(m["lab"]["equivalence"])
            with st.form("sql-" + m["id"]):
                sql = st.text_area("SQL · DuckDB", m["lab"]["sql"], height=160, key="sqlquery-" + m["id"])
                run_sql = st.form_submit_button("Run SQL comparison")
            if run_sql:
                try:
                    answer = sql_query(sql, EVALUATION_TIMES[variant])
                    st.dataframe(
                        pd.DataFrame(answer["rows"], columns=answer["columns"]),
                        hide_index=True,
                        width="stretch",
                    )
                except (ValueError, RuntimeError) as exc:
                    st.error(str(exc))
        st.caption(
            "Queries run in real Prometheus against repeatable synthetic measurements. They never contact your production systems."
        )


def assessment(m):
    index = MISSIONS.index(m)
    st.markdown("### Explain it. Then prove it.")
    st.write(
        "Answer five questions and solve the practical challenge. At least 80% plus evidence that passes both scenarios earns the badge."
    )
    if index > summary["next"]:
        previous = MISSIONS[summary["next"]]
        st.info(
            "Complete "
            + previous["title"]
            + " to unlock this assessment. You can preview all its lessons and experiments now."
        )
        return
    result = st.session_state.get("result-" + learner + m["id"])
    if result:
        if result["passed"]:
            st.success(m["badge"] + " earned · " + str(result["score"]) + "% · 100 XP on your first pass")
            if index + 1 < len(MISSIONS):
                st.button(
                    "Continue the story →",
                    type="primary",
                    on_click=go_to,
                    args=("Mission", MISSIONS[index + 1]["id"]),
                )
        else:
            st.warning("Some evidence needs another look. Your quiz score: " + str(result["score"]) + "%.")
        for r in result["lab"]["reports"]:
            st.write(("✓ " if r["passed"] else "↻ ") + f"Scenario {r['scenario']}: " + r["message"])
        for i, r in enumerate(result["feedback"], 1):
            with st.expander(f"{'✓' if r['correct'] else '↻'} Question {i} · why this answer matters"):
                st.write(r["answer"])
                st.write(r["explanation"])
        if st.button("Try a fresh assessment", key="retry-" + m["id"]):
            del st.session_state["result-" + learner + m["id"]]
            st.rerun()
        return
    attempt = store.attempt(learner, m["id"])
    questions = {q["id"]: q for q in m["questions"]}
    with st.form("proof-" + attempt["id"]):
        answers = {}
        for n, ident in enumerate(json.loads(attempt["questions"]), 1):
            q = questions[ident]
            answers[ident] = st.radio(
                f"{n}. {q['prompt']}",
                list(range(len(q["options"]))),
                format_func=lambda i, q=q: q["options"][i],
                index=None,
                key=attempt["id"] + ident,
            )
        st.divider()
        st.write("**Practical goal:** " + m["lab"]["goal"])
        plan = plan_controls(m, "proof-" + attempt["id"], challenge=True)
        grade = st.form_submit_button("Check my evidence and earn the badge", type="primary")
    if grade:
        if any(v is None for v in answers.values()):
            st.info("Choose an answer for every question first.")
        else:
            with st.spinner("Checking your evidence in both scenarios…"):
                st.session_state["result-" + learner + m["id"]] = store.grade(
                    learner, attempt["id"], answers, plan
                )
            st.rerun()


def learn(m):
    choices = {c["id"]: c for c in m["concepts"]}
    selected = st.selectbox(
        "One concept at a time",
        list(choices),
        format_func=lambda ident: choices[ident]["title"],
        key="concept-" + m["id"],
    )
    c = choices[selected]
    st.markdown(
        '<div class="path"><span class="active">01 Predict</span><span>02 Watch</span><span>03 Experiment</span><span>04 Explain</span><span>05 Remember</span></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Before you watch: make a prediction", expanded=True):
        q = c["check"]
        with st.form("prediction-" + learner + c["id"]):
            choice = st.radio(
                q["prompt"],
                list(range(len(q["options"]))),
                format_func=lambda i: q["options"][i],
                index=None,
                key="predictchoice-" + learner + c["id"],
            )
            predict = st.form_submit_button("Make my prediction")
        if predict:
            if choice is None:
                st.info("Choose the answer you think is most likely.")
            else:
                r = store.answer(learner, c["id"], choice)
                st.session_state["prediction-result-" + learner + c["id"]] = r
                store.event(learner, "prediction", c["id"])
        r = st.session_state.get("prediction-result-" + learner + c["id"])
        if r:
            (st.success if r["correct"] else st.info)(
                ("You predicted it. " if r["correct"] else "A useful discovery. ") + r["explanation"]
            )
            st.caption("This practice is ungraded. The review queue will revisit this idea after a delay.")
    animation.show(c)
    st.markdown("### Put the picture into words")
    st.write(c["explanation"])
    tip("A FAMILIAR CONNECTION", c["analogy"])
    with st.expander("Walk through the example"):
        st.write(c["example"])
    with st.expander("Connect it to SQL"):
        st.write(c["sql_connection"])
    tip("THE IDEA TO KEEP", c["remember"])
    with st.expander("Explain it back in your own words"):
        previous = next((n["body"] for n in summary["notes"] if n["concept"] == c["id"]), "")
        with st.form("reflection-" + learner + c["id"]):
            text = st.text_area(
                "What changed, why did it change, and what would you expect next?",
                value=previous,
                height=110,
                max_chars=2000,
            )
            save = st.form_submit_button("Save my explanation")
        if save:
            store.note(learner, c["id"], text)
            store.event(learner, "explanation", c["id"])
            st.success("Saved in your private evidence notebook.")
        st.caption(
            "Name the measurement or signal, its identity, and the evidence. A saved explanation is self-reported practice; it does not award a badge."
        )
    with st.expander("Read the animation without motion"):
        for i, step in enumerate(c["animation"].get("steps", c["animation"].get("frames", [])), 1):
            st.write(str(i) + ". " + step.get("explanation", step.get("narration", "")))
            if "nodes" in step:
                st.write(" · ".join(n["label"] + ": " + str(n["value"]) for n in step["nodes"]))
    with st.expander("Go to the original references"):
        for source in sources_for(c):
            st.link_button(source["title"], source["url"])


page = st.session_state.nav
if page == "Start":
    eyebrow("A VISUAL OBSERVABILITY LEARNING STUDIO")
    left, right = st.columns([1, 1.05], gap="large")
    with left:
        st.markdown(
            '<div class="hero-title">Understand the signal.<br><em>Own the story.</em></div><p class="hero-copy">Start with one number. Watch it become a measurement, a query, and a request journey. Learn PromQL and OpenTelemetry through pictures you control and evidence you can explain.</p>',
            unsafe_allow_html=True,
        )
        next_m = MISSIONS[min(summary["next"], len(MISSIONS) - 1)]
        st.button(
            "Continue my story →" if summary["done"] else "Start with one number →",
            type="primary",
            on_click=go_to,
            args=("Mission", next_m["id"]),
        )
        st.markdown(
            '<p class="micro">No observability experience needed. Start in five minutes.</p>',
            unsafe_allow_html=True,
        )
    with right:
        animation.hero()
    st.markdown(
        '<div class="stats"><div class="stat"><b>22</b><span>guided missions</span></div><div class="stat"><b>70</b><span>illustrated concepts</span></div><div class="stat"><b>2 real engines</b><span>Prometheus + Python SDK</span></div><div class="stat"><b>Your own pace</b><span>practice, review, and badges</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="small-title">One story. Four acts.</div>', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for i, (col, act) in enumerate(zip(cols, COURSE["acts"])):
        with col:
            st.markdown(
                f'<div class="act-card"><div class="num">ACT {i + 1:02d}</div><h3>{html.escape(act["title"])}</h3><p>{html.escape(act["description"])}</p></div>',
                unsafe_allow_html=True,
            )
            first = next(m for m in MISSIONS if m["act"] == i)
            st.button(
                "Explore this act ↗",
                key="act-" + str(i),
                on_click=go_to,
                args=("Mission", first["id"]),
                width="stretch",
            )
    st.divider()
    a, b = st.columns(2, gap="large")
    with a:
        tip(
            "UNDERSTANDING BEFORE SYNTAX",
            "First see what a counter, gauge, bucket, or span means. Then change an input and explain its effect.",
        )
    with b:
        tip(
            "PRACTICE THAT COMES BACK",
            "Missed ideas enter your review queue. Correct reviews spread across days, so you revisit the meaning rather than only collect badges.",
        )
elif page == "Journey":
    eyebrow("YOUR MAP FROM THE FIRST NUMBER TO AN INVESTIGATION")
    heading(
        "A clear path. A story worth following.",
        "Every lesson is open to preview. Assessments progress in order, one practical mission at a time.",
    )
    for act_index, act in enumerate(COURSE["acts"]):
        st.markdown("### " + act["title"])
        group = [m for m in MISSIONS if m["act"] == act_index]
        for offset in range(0, len(group), 3):
            for col, m in zip(st.columns(3), group[offset : offset + 3]):
                with col:
                    status = "COMPLETED" if m["id"] in summary["done"] else "PREVIEW OPEN"
                    st.markdown(
                        f'<div class="mission-card"><span class="chip">{status}</span><h3>{html.escape(m["title"])}</h3><p>{len(m["concepts"])} concepts · {m["minutes"]} min suggested pace</p></div>',
                        unsafe_allow_html=True,
                    )
                    st.button(
                        "Open mission →",
                        key="open-" + m["id"],
                        on_click=go_to,
                        args=("Mission", m["id"]),
                        width="stretch",
                    )
elif page == "Mission":
    m = mission(st.session_state.current)
    eyebrow(f"ACT {m['act'] + 1} · MISSION {MISSIONS.index(m) + 1:02d} OF 22")
    heading(m["title"], m["objective"])
    st.markdown(
        f'<div class="lesson-meta"><span class="chip">{html.escape(m["badge"])}</span><span>{len(m["concepts"])} ideas · one practical challenge</span></div>',
        unsafe_allow_html=True,
    )
    learn_tab, lab_tab, proof_tab = st.tabs(["Learn the story", "Experiment", "Earn the badge"])
    with learn_tab:
        learn(m)
    with lab_tab:
        experiment(m)
    with proof_tab:
        assessment(m)
elif page == "Review":
    eyebrow("A LITTLE RETRIEVAL. A STRONGER MEMORY.")
    heading(
        "Bring the idea back.",
        "Answer without the worked example. A missed concept returns soon; correct reviews spread across 1, 3, 7, 14, and 30 days.",
    )
    due = summary["due"]
    if not due:
        st.success("No reviews are due right now.")
        if summary["reviews"]:
            next_time = min(r["due"] for r in summary["reviews"])
            st.caption("Next review: " + datetime.fromtimestamp(next_time, UTC).strftime("%b %d, %H:%M UTC"))
        st.button("Keep learning →", on_click=go_to, args=("Journey",))
    else:
        for row in due[:5]:
            c = CONCEPTS[row["concept"]]
            q = c["check"]
            with st.container(border=True):
                st.markdown("#### " + c["title"])
                with st.form("review-" + learner + c["id"]):
                    choice = st.radio(
                        q["prompt"],
                        list(range(len(q["options"]))),
                        format_func=lambda i, q=q: q["options"][i],
                        index=None,
                        key="reviewchoice-" + c["id"],
                    )
                    submit = st.form_submit_button("Recall and check")
                if submit and choice is not None:
                    result = store.answer(learner, c["id"], choice)
                    store.event(learner, "review", c["id"])
                    st.session_state["review-result-" + learner + c["id"]] = result
                    (st.success if result["correct"] else st.info)(result["explanation"])
                    st.caption("This idea has been scheduled for a later review.")
elif page == "Ask a question":
    eyebrow("A PATIENT GUIDE, GROUNDED IN THIS COURSE")
    heading(
        "Ask until the picture makes sense.",
        "Get a plain-language explanation, a worked example, a common mistake, and a question to check your understanding.",
    )
    selected = st.selectbox(
        "What concept are you learning?",
        [""] + list(CONCEPTS),
        format_func=lambda ident: (
            "Find the relevant concept for me" if not ident else CONCEPTS[ident]["title"]
        ),
    )
    use_ai = st.checkbox("Use the AI mentor", value=tutor.configured(), disabled=not tutor.configured())
    st.caption(
        "When enabled, your question and course excerpts go to the configured AI service. The course guide works without an API key. Usage logs contain metadata, not your full question or explanation."
    )
    with st.form("ask"):
        question = st.text_area(
            "Your question",
            placeholder="Why does one request increase several histogram buckets?",
            height=120,
            max_chars=2500,
        )
        ask = st.form_submit_button("Help me understand →", type="primary")
    if ask and question.strip():
        allow = use_ai and store.reserve_call(learner, global_limit=int(os.getenv("TUTOR_DAILY_LIMIT", "80")))
        if use_ai and not allow:
            st.info("The AI allowance is used for today. The course guide is still available.")
        with st.spinner("Connecting your question to the course…"):
            result = tutor.ask(question, selected, allow_generation=allow)
        st.session_state.last_answer = result
        store.event(learner, "tutor", selected)
    result = st.session_state.get("last_answer")
    if result:
        st.caption(result["mode"] + " · " + result["retrieval_mode"])
        a = result["answer"]
        st.write(a["explanation"])
        for field, label in [
            ("analogy", "Make it familiar"),
            ("worked_example", "Work through the authored course example"),
            ("common_mistake", "Avoid this trap"),
            ("check_yourself", "Try explaining this"),
        ]:
            if a.get(field):
                st.markdown("#### " + label)
                st.write(a[field])
        with st.expander("Inspect the evidence behind this explanation"):
            for doc in result["docs"]:
                st.write("**" + doc["title"] + "**")
                st.write(doc["text"][:1600])
                for source in doc["sources"]:
                    st.link_button(source["title"], source["url"], key=doc["id"] + source["url"])
elif page == "My evidence":
    eyebrow("YOUR WORK, YOUR WORDS, YOUR PROGRESS")
    heading(
        "Understanding you can point to.",
        "Badges mark completed assessments. Your notebook keeps the reasoning you wrote along the way.",
    )
    a, b, c = st.columns(3)
    a.metric("Missions completed", len(summary["done"]))
    b.metric("Concepts practiced", summary["practiced"])
    c.metric("Reviewed across three occasions", summary["retained"])
    if summary["badges"]:
        for offset in range(0, len(summary["badges"]), 3):
            for col, row in zip(st.columns(3), summary["badges"][offset : offset + 3]):
                m = mission(row["mission"])
                with col:
                    st.markdown(
                        f'<div class="badge"><div class="badge-icon">◈</div><strong>{html.escape(m["badge"])}</strong><span>{row["score"]}% · both scenarios passed</span></div>',
                        unsafe_allow_html=True,
                    )
    else:
        st.info("Your first badge is waiting in Mission 1. Predict, experiment, and complete its assessment.")
    report = store.report(learner)
    st.download_button(
        "Download my learning card",
        milestone(report),
        file_name="signalstory-milestone.svg",
        mime="image/svg+xml",
    )
    st.download_button(
        "Download my private evidence notebook",
        json.dumps(report, indent=2),
        file_name="signalstory-private-evidence.json",
        mime="application/json",
    )
    for note in summary["notes"]:
        with st.expander(CONCEPTS[note["concept"]]["title"]):
            st.text(note["body"])
    st.caption(
        "The share card contains totals only. Your private notebook contains your explanations. These are learning records, not an accredited certification."
    )
elif page == "Word guide":
    eyebrow("PLAIN WORDS FOR UNFAMILIAR IDEAS")
    heading("Keep the meaning close.", "Look up a term, then return to the story.")
    query = st.text_input("Find a word", placeholder="counter, bucket, span, cardinality…")
    for word, definition in COURSE["glossary"].items():
        if query.lower() in word.lower() or query.lower() in str(definition).lower():
            st.markdown("#### " + word)
            st.write(definition)
st.markdown(
    '<div class="footer">SignalStory · Visual observability, from the first measurement to independent reasoning. Built with Python. Original courses by Siva Babu.</div>',
    unsafe_allow_html=True,
)
