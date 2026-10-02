import json

from streamlit.testing.v1 import AppTest

from signalstory.course import ROOT, concepts, missions


def press(app, label):
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception


def test_beginner_can_predict_explain_experiment_and_earn_first_badge(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGNALSTORY_DB", str(tmp_path / "app.sqlite3"))
    app = AppTest.from_file(ROOT / "app.py", default_timeout=20).run()
    assert not app.exception
    press(app, "Start with one number →")
    ident = missions()[0]["concepts"][0]["id"]
    next(r for r in app.radio if r.key.startswith("predictchoice-")).set_value(
        concepts()[ident]["check"]["answer"]
    )
    press(app, "Make my prediction")
    assert any("You predicted it." in x.value for x in app.success)
    app.text_area[0].set_value("A sample is a value at one time, with identity and a unit.")
    press(app, "Save my explanation")
    press(app, "Run the experiment ↗")
    assert app.dataframe
    attempt = next(r for r in app.radio if r.label.startswith("1. ")).key[:32]
    questions = {q["id"]: q for q in missions()[0]["questions"]}
    for radio in app.radio:
        if radio.key.startswith(attempt):
            radio.set_value(questions[radio.key[32:]]["answer"])
    app.text_area(key="proof-" + attempt + "query").set_value(missions()[0]["lab"]["solution"])
    press(app, "Check my evidence and earn the badge")
    assert any("earned" in x.value for x in app.success)
    assert app.session_state["profile"]
    press(app, "Continue the story →")
    assert app.session_state["current"] == "promql-01"


def test_every_mission_renders_and_offline_tutor_works(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGNALSTORY_DB", str(tmp_path / "preview.sqlite3"))
    app = AppTest.from_file(ROOT / "app.py", default_timeout=20).run()
    app.radio(key="nav").set_value("Mission")
    for m in missions():
        app.selectbox(key="current").set_value(m["id"]).run()
        assert not app.exception, m["id"]
    app.radio(key="nav").set_value("Ask a question").run()
    app.checkbox[0].uncheck()
    app.text_area[0].set_value("What makes a histogram bucket cumulative?")
    press(app, "Help me understand →")
    assert app.session_state["last_answer"]["mode"] == "Course guide"
    json.dumps(app.session_state["last_answer"]["answer"])
