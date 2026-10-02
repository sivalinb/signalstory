"""Owned progress, deterministic assessment, review scheduling, and bounded usage."""

import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from . import labs
from .course import ROOT, concepts, mission, missions


class Progress:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / ".runtime/progress.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS badges(profile TEXT, mission TEXT, score INTEGER, at INTEGER,
                PRIMARY KEY(profile,mission));
            CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, profile TEXT, mission TEXT,
                questions TEXT, result TEXT, at INTEGER);
            CREATE TABLE IF NOT EXISTS reviews(profile TEXT, concept TEXT, repetitions INTEGER,
                due INTEGER, last_correct INTEGER, PRIMARY KEY(profile,concept));
            CREATE TABLE IF NOT EXISTS notes(profile TEXT, concept TEXT, body TEXT, at INTEGER,
                PRIMARY KEY(profile,concept));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, profile TEXT, event TEXT,
                target TEXT, at INTEGER);
            CREATE TABLE IF NOT EXISTS calls(profile TEXT, day TEXT, calls INTEGER,
                PRIMARY KEY(profile,day));
            """)

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        try:
            with con:
                yield con
        finally:
            con.close()

    @staticmethod
    def identity(token):
        return hashlib.sha256(token.strip().encode()).hexdigest()

    def create(self, name="Explorer"):
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute("INSERT INTO profiles VALUES (?,?)", (self.identity(token), name[:40] or "Explorer"))
        return self.identity(token), token

    def resume(self, token):
        if not isinstance(token, str) or len(token) > 160:
            return None
        identity = self.identity(token)
        with self.db() as db:
            return (
                identity if db.execute("SELECT 1 FROM profiles WHERE id=?", (identity,)).fetchone() else None
            )

    @staticmethod
    def owner(db, profile):
        if not db.execute("SELECT 1 FROM profiles WHERE id=?", (profile,)).fetchone():
            raise PermissionError("Unknown learner profile")

    def summary(self, profile, now=None):
        now = int(time.time()) if now is None else now
        with self.db() as db:
            self.owner(db, profile)
            badges = [
                dict(x) for x in db.execute("SELECT mission,score,at FROM badges WHERE profile=?", (profile,))
            ]
            reviews = [dict(x) for x in db.execute("SELECT * FROM reviews WHERE profile=?", (profile,))]
            notes = [
                dict(x) for x in db.execute("SELECT concept,body FROM notes WHERE profile=?", (profile,))
            ]
        done = {x["mission"] for x in badges}
        next_index = next((i for i, m in enumerate(missions()) if m["id"] not in done), len(missions()))
        return {
            "badges": badges,
            "done": done,
            "next": next_index,
            "xp": len(done) * 100,
            "due": [r for r in reviews if r["due"] <= now],
            "reviews": reviews,
            "notes": notes,
            "practiced": len(reviews),
            "retained": sum(r["repetitions"] >= 3 for r in reviews),
        }

    def event(self, profile, event, target=""):
        if event not in {
            "mission_open",
            "lab_run",
            "prediction",
            "review",
            "mission_pass",
            "tutor",
            "explanation",
        }:
            raise ValueError("Unknown learning event")
        with self.db() as db:
            self.owner(db, profile)
            db.execute(
                "INSERT INTO events(profile,event,target,at) VALUES (?,?,?,?)",
                (profile, event, str(target)[:100], int(time.time())),
            )

    def answer(self, profile, concept_id, choice, now=None):
        check = concepts()[concept_id]["check"]
        if type(choice) is not int or not 0 <= choice < len(check["options"]):
            raise ValueError("Choose one answer")
        correct = choice == check["answer"]
        now = int(time.time()) if now is None else now
        with self.db() as db:
            self.owner(db, profile)
            row = db.execute(
                "SELECT * FROM reviews WHERE profile=? AND concept=?", (profile, concept_id)
            ).fetchone()
            repetitions = row["repetitions"] if row else 0
            # Early practice does not manufacture spaced repetitions.
            if correct and (row is None or row["due"] <= now):
                repetitions = min(repetitions + 1, 5)
            if not correct:
                repetitions = 0
            wait = [0, 1, 3, 7, 14, 30][repetitions] * 86400 if correct else 600
            due = row["due"] if correct and row and row["due"] > now else now + wait
            db.execute(
                "INSERT INTO reviews VALUES (?,?,?,?,?) ON CONFLICT(profile,concept) DO UPDATE SET "
                "repetitions=excluded.repetitions,due=excluded.due,last_correct=excluded.last_correct",
                (profile, concept_id, repetitions, due, int(correct)),
            )
        return {
            "correct": correct,
            "explanation": check["explanation"],
            "answer": check["options"][check["answer"]],
            "due": due,
            "repetitions": repetitions,
        }

    def note(self, profile, concept_id, body):
        if concept_id not in concepts():
            raise ValueError("Unknown concept")
        body = body.strip()[:2000]
        with self.db() as db:
            self.owner(db, profile)
            db.execute(
                "INSERT INTO notes VALUES (?,?,?,?) ON CONFLICT(profile,concept) DO UPDATE SET "
                "body=excluded.body,at=excluded.at",
                (profile, concept_id, body, int(time.time())),
            )

    def attempt(self, profile, mission_id):
        index = next(i for i, m in enumerate(missions()) if m["id"] == mission_id)
        if index > self.summary(profile)["next"]:
            raise PermissionError("Complete the preceding mission first")
        with self.db() as db:
            previous = db.execute(
                "SELECT * FROM attempts WHERE profile=? AND mission=? AND result IS NULL "
                "ORDER BY at DESC LIMIT 1",
                (profile, mission_id),
            ).fetchone()
            if previous:
                return dict(previous)
            ids = secrets.SystemRandom().sample([q["id"] for q in mission(mission_id)["questions"]], 5)
            row = {
                "id": secrets.token_hex(16),
                "profile": profile,
                "mission": mission_id,
                "questions": json.dumps(ids),
                "result": None,
                "at": int(time.time()),
            }
            db.execute("INSERT INTO attempts VALUES (:id,:profile,:mission,:questions,:result,:at)", row)
        return row

    def grade(self, profile, attempt_id, answers, plan):
        with self.db() as db:
            self.owner(db, profile)
            row = db.execute(
                "SELECT * FROM attempts WHERE id=? AND profile=?", (attempt_id, profile)
            ).fetchone()
        if not row:
            raise PermissionError("This attempt belongs to another profile")
        if row["result"]:
            return json.loads(row["result"])
        m = mission(row["mission"])
        if missions().index(m) > self.summary(profile)["next"]:
            raise PermissionError("This mission is locked")
        questions = {q["id"]: q for q in m["questions"]}
        feedback = [
            dict(
                id=ident,
                concept=questions[ident]["concept"],
                correct=type(answers.get(ident)) is int and answers[ident] == questions[ident]["answer"],
                explanation=questions[ident]["explanation"],
                answer=questions[ident]["options"][questions[ident]["answer"]],
            )
            for ident in json.loads(row["questions"])
        ]
        score = 20 * sum(f["correct"] for f in feedback)
        lab = labs.grade(m, plan)
        result = {
            "score": score,
            "lab": lab,
            "passed": score >= 80 and lab["passed"],
            "feedback": feedback,
            "mission": m["id"],
        }
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT result FROM attempts WHERE id=? AND profile=?", (attempt_id, profile)
            ).fetchone()
            if existing["result"]:
                return json.loads(existing["result"])
            db.execute(
                "UPDATE attempts SET result=? WHERE id=? AND profile=?",
                (json.dumps(result), attempt_id, profile),
            )
            if result["passed"]:
                db.execute(
                    "INSERT OR IGNORE INTO badges VALUES (?,?,?,?)",
                    (profile, m["id"], score, int(time.time())),
                )
        for item in feedback:
            if not item["correct"] and item["concept"] in concepts():
                c = concepts()[item["concept"]]["check"]
                self.answer(profile, item["concept"], (c["answer"] + 1) % len(c["options"]))
        if result["passed"]:
            self.event(profile, "mission_pass", m["id"])
        return result

    def reserve_call(self, profile, per_profile=8, global_limit=80):
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with self.db() as db:
            self.owner(db, profile)
            db.execute("BEGIN IMMEDIATE")
            total = db.execute("SELECT COALESCE(SUM(calls),0) FROM calls WHERE day=?", (day,)).fetchone()[0]
            row = db.execute("SELECT calls FROM calls WHERE profile=? AND day=?", (profile, day)).fetchone()
            if total >= global_limit or (row and row["calls"] >= per_profile):
                return False
            db.execute(
                "INSERT INTO calls VALUES (?,?,1) ON CONFLICT(profile,day) DO UPDATE SET calls=calls+1",
                (profile, day),
            )
        return True

    def report(self, profile):
        s = self.summary(profile)
        return {
            "product": "SignalStory",
            "curriculum": "signalstory-v1",
            "badges": s["badges"],
            "concepts_practiced": s["practiced"],
            "spaced_reviews_completed": s["retained"],
            "explanations": s["notes"],
            "note": "Practice evidence; not an accredited certification.",
        }
