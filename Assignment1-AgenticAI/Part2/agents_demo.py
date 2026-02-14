import json
import re
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Use 127.0.0.1 to avoid localhost resolution/firewall quirks on some Windows setups
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "smollm:1.7b"


# -----------------------------
# Ollama helper 
# -----------------------------
def ollama_chat(
    messages: List[Dict[str, str]],
    model: str = MODEL_NAME,
    temperature: float = 0.4,
    timeout_seconds: int = 300,
    num_predict: int = 220,
) -> str:
    """
    Calls Ollama's /api/chat endpoint and returns the assistant text.

    Key reliability settings:
    - timeout_seconds: higher timeout for slower machines / first model load
    - num_predict: caps output length to prevent the model from rambling/looping
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            obj = json.loads(raw)
            return obj.get("message", {}).get("content", "").strip()
    except Exception as e:
        raise RuntimeError(
            "Failed to call Ollama. Make sure Ollama is running and the model is pulled.\n"
            f"Endpoint: {OLLAMA_URL}\nModel: {model}\nError: {e}"
        )


# -----------------------------
# JSON extraction + enforcement
# -----------------------------
def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Finds if there is a JSON object inside text, if so returns it else return None.
    """
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    candidate = match.group(0).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def clean_tags(tags: Any) -> List[str]:
    """Convert tags to a clean list of unique strings."""
    if not isinstance(tags, list):
        return []

    cleaned: List[str] = []
    seen = set()
    for t in tags:
        if not isinstance(t, str):
            continue
        x = t.strip()
        if not x:
            continue
        key = x.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(x)
    return cleaned


def finalize_output(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finalizer step: strictly enforce requirements:
    - exactly 3 tags
    - one-sentence summary <= 25 words
    - return dict with keys: tags, summary
    """
    tags = clean_tags(obj.get("tags"))
    summary = obj.get("summary")

    # Exactly 3 tags:
    if len(tags) > 3:
        tags = tags[:3]
    while len(tags) < 3:
        tags.append("general")

    return {"tags": tags, "summary": summary}


# -----------------------------
# Agents
# -----------------------------
def planner_agent(title: str, content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Planner agent: proposes topical tags and a short summary.
    Output should be JSON only (but finalizer will still enforce).
    """
    system = (
        "You are the Planner agent. Return ONLY valid JSON.\n"
        "Keys: tags, summary.\n"
        "- tags: JSON array of strings (3 candidates allowed)\n"
        "- summary: ONE sentence, <= 25 words\n"
        "No markdown. No extra text."
    )

    user = (
        f"TITLE:\n{title}\n\n"
        f"CONTENT:\n{content}\n\n"
        "Produce candidate topical tags and a one-sentence <=25-word summary."
    )

    text = ollama_chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.5,
        timeout_seconds=300,
        num_predict=220,
    )

    parsed = extract_json_from_text(text) or {}
    return text, parsed


def reviewer_agent(planner_json: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Reviewer agent: fixes Planner output to match strict constraints.
    IMPORTANT: Do NOT resend the full blog here — it slows the model and can cause timeouts.
    """
    system = (
        "You are the Reviewer. Output ONLY valid JSON with keys tags and summary. "
        "tags must contain EXACTLY 3 strings. summary must be ONE sentence with <=25 words."
        "Don't generate any text outside the JSON. If the Planner output has issues, fix them and return corrected JSON. "
        "Do not return Python code or markdown or any other language code or markup, just JSON."
    )

    user = (
        f"PLANNER_OUTPUT_JSON:\n{json.dumps(planner_json, ensure_ascii=False)}\n\n"
        "Fix any issues and return corrected JSON only."
    )

    text = ollama_chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        timeout_seconds=300,
        num_predict=180,
    )

    parsed = extract_json_from_text(text) or {}
    return text, parsed

def finalizer_agent(reviewer_json: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Finalizer agent: produces the final, polished output.
    Takes the Reviewer's feedback and creates the definitive tags and summary.
    This is the third agent in the workflow: Planner -> Reviewer -> Finalizer
    """
    system = (
        "You are the Finalizer agent. Your job is to produce the final, polished output.\n"
        "Based on the Reviewer's feedback, create the best possible tags and summary.\n\n"
        "Return ONLY valid JSON with these exact keys:\n"
        "- tags: array of EXACTLY 3 topical, specific tags (strings)\n"
        "- summary: ONE sentence, <=25 words, ends with period\n\n"
        "Make sure tags are:\n"
        "- Topical and specific to the blog content\n"
        "- Multi-word phrases when possible (e.g., 'local models' not just 'models')\n"
        "- Not generic (avoid 'general', 'content', 'information')\n\n"
        "Make sure summary is:\n"
        "- Concise and clear\n"
        "- Captures the main point\n"
        "- Exactly one sentence\n"
        "- 25 words or fewer\n\n"
        "No markdown. No extra text. No code. Just pure JSON."
    )

    user = (
        f"REVIEWER_OUTPUT:\n{json.dumps(reviewer_json, ensure_ascii=False)}\n\n"
        "Produce the final, polished tags and summary. "
        "Use the Reviewer's feedback to make the best possible output."
    )

    text = ollama_chat(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.1,  # Very low temperature for consistent final output
        timeout_seconds=300,
        num_predict=180,
    )

    parsed = extract_json_from_text(text) or {}
    return text, parsed



# -----------------------------
# Workflow runner
# -----------------------------
def run_agent_workflow(title: str, content: str) -> Dict[str, Any]:
    """
    Orchestrates Planner -> Reviewer -> Finalizer.
    Prints transcript + final strict JSON.
    """
    print("--- PLANNER TRANSCRIPT ---")
    planner_text, planner_obj = planner_agent(title, content)
    print(planner_text)
    print()

    print("--- REVIEWER TRANSCRIPT ---")
    reviewer_text, reviewer_obj = reviewer_agent(planner_obj)
    print(reviewer_text)
    print()

    print("--- FINAL PUBLISH OUPUT ---")
    finalizer_text, finalizer_obj = finalizer_agent(reviewer_obj)
    print(finalizer_text)
    print()

    print("--- FINAL PUBLISH OUTPUT ---")
    print(json.dumps(finalizer_obj, indent=2, ensure_ascii=False))
    return finalizer_obj


def main() -> None:
    title = "Understanding Distributed Systems and Consensus Algorithms"

    content = (
        "Distributed systems are computing architectures that rely on multiple machines "
        "working together to achieve a common goal. Unlike traditional single-machine systems, "
        "distributed systems coordinate across networks to provide scalability, fault tolerance, "
        "and high availability. Key challenges include maintaining data consistency, handling "
        "network partitions, and achieving consensus among nodes.\n\n"
        
        "Consensus algorithms like Paxos and Raft enable distributed systems to agree on shared "
        "state even when some nodes fail or messages are delayed. The Paxos algorithm, while powerful, "
        "is notoriously complex to implement correctly. Raft was designed as a more understandable "
        "alternative that achieves the same goals through leader election and log replication.\n\n"
        
        "Modern distributed databases and cloud systems rely heavily on these consensus algorithms "
        "to ensure data integrity and system reliability. Understanding how these algorithms work is "
        "essential for building robust distributed applications that can handle real-world failures "
        "and network issues."
    )

    run_agent_workflow(title, content)


if __name__ == "__main__":
    main()
