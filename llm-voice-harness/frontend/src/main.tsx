import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type Scenario = {
  id: number;
  name: string;
  transcript: string;
  goal: "book_appointment" | "refill_medication" | "get_office_hours";
};

type Run = {
  id: number;
  status: "pass" | "fail";
  tool_called: string;
  tool_args: Record<string, unknown>;
  evaluation: { pass: boolean; reasons: string[] };
  created_at: string;
};

const API = "http://127.0.0.1:8000";

function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [name, setName] = useState("Refill test");
  const [transcript, setTranscript] = useState("I am John Doe. Need refill for lisinopril.");
  const [goal, setGoal] = useState<Scenario["goal"]>("refill_medication");

  const refresh = async () => {
    const [s, r] = await Promise.all([
      fetch(`${API}/scenarios`).then((x) => x.json()),
      fetch(`${API}/runs`).then((x) => x.json()),
    ]);
    setScenarios(s);
    setRuns(r);
  };

  useEffect(() => {
    void refresh();
  }, []);

  const createScenario = async () => {
    await fetch(`${API}/scenarios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, transcript, goal, expected: {} }),
    });
    await refresh();
  };

  const runAll = async () => {
    await fetch(`${API}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    await refresh();
  };

  return (
    <main style={{ fontFamily: "Arial", maxWidth: 980, margin: "0 auto", padding: 16 }}>
      <h1>LLM Voice Agent Harness</h1>
      <section>
        <h3>Create Scenario</h3>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="name" />
        <select value={goal} onChange={(e) => setGoal(e.target.value as Scenario["goal"])}>
          <option value="book_appointment">book_appointment</option>
          <option value="refill_medication">refill_medication</option>
          <option value="get_office_hours">get_office_hours</option>
        </select>
        <br />
        <textarea
          style={{ width: "100%", minHeight: 90 }}
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
        />
        <button onClick={() => void createScenario()}>Save Scenario</button>
        <button onClick={() => void runAll()} style={{ marginLeft: 8 }}>
          Run Batch
        </button>
      </section>

      <section>
        <h3>Scenarios</h3>
        <ul>
          {scenarios.map((s) => (
            <li key={s.id}>
              <b>{s.name}</b> [{s.goal}] — {s.transcript}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Runs</h3>
        <ul>
          {runs.map((r) => (
            <li key={r.id}>
              #{r.id} <b>{r.status.toUpperCase()}</b> | tool={r.tool_called} | reasons=
              {r.evaluation.reasons.join("; ")}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
