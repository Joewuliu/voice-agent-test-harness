import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "runs.db"


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                transcript TEXT NOT NULL,
                goal TEXT NOT NULL,
                expected TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                transcript TEXT NOT NULL,
                tool_called TEXT NOT NULL,
                tool_args TEXT NOT NULL,
                tool_response TEXT NOT NULL,
                evaluation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(scenario_id) REFERENCES scenarios(id)
            )
            """
        )


def insert_run(
    scenario_id: int,
    status: str,
    transcript: str,
    tool_called: str,
    tool_args: dict,
    tool_response: dict,
    evaluation: dict,
) -> int:
    with conn() as c:
        cur = c.execute(
            """
            INSERT INTO runs (scenario_id, status, transcript, tool_called, tool_args,
             tool_response, evaluation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_id,
                status,
                transcript,
                tool_called,
                json.dumps(tool_args, default=str),
                json.dumps(tool_response, default=str),
                json.dumps(evaluation, default=str),
                datetime.utcnow().isoformat(),
            ),
        )
        return int(cur.lastrowid)


def parse_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "scenario_id": row["scenario_id"],
        "status": row["status"],
        "transcript": row["transcript"],
        "tool_called": row["tool_called"],
        "tool_args": json.loads(row["tool_args"]),
        "tool_response": json.loads(row["tool_response"]),
        "evaluation": json.loads(row["evaluation"]),
        "created_at": row["created_at"],
    }
