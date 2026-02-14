from typing import TypedDict, Dict, Any, Literal
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
import json
import re


# ============================================================================
# STEP 1: Define the Shared State (AgentState)
# ============================================================================
class AgentState(TypedDict):
    """
    Shared memory for all agents in the graph.

    Fields:
      title             blog title  (input)
      content           blog body   (input)
      task              instruction string
      llm               ChatOllama instance
      planner_proposal  dict with "tags" and "summary"
      reviewer_feedback dict with "has_issues" and "issues"
      turn_count        loop counter (prevents infinite loops)
    """
    title: str
    content: str
    task: str
    llm: Any
    planner_proposal: Dict[str, Any]
    reviewer_feedback: Dict[str, Any]
    turn_count: int


# ============================================================================
# Helper: robust JSON extraction for small LLMs
# ============================================================================
def extract_json_from_text(text: str) -> dict:
    text = text.strip()

    # Strategy 1: strip markdown fences
    if "```" in text:
        # grab content between first pair of triple-backticks
        parts = text.split("```")
        for part in parts[1:]:
            # skip optional language tag on the same line
            candidate = part.split("\n", 1)[-1] if "\n" in part else part
            candidate = candidate.strip()
            if candidate.startswith("{"):
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

    # Strategy 2: find the first { ... } block in the text
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        candidate = text[brace_start:brace_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Strategy 3: regex for tags array + summary
    tags_match = re.search(r'\[([^\]]+)\]', text)
    summary_match = re.search(r'summary["\s:]+([^"}\]]+)', text, re.IGNORECASE)

    tags = []
    if tags_match:
        raw = tags_match.group(1)
        tags = [t.strip().strip('"').strip("'") for t in raw.split(",")]
        tags = [t for t in tags if t][:3]

    summary = ""
    if summary_match:
        summary = summary_match.group(1).strip().strip('"').strip("'")

    if tags and summary:
        return {"tags": tags, "summary": summary}

    raise ValueError(f"Could not parse JSON from LLM output:\n{text}")


# ============================================================================
# STEP 2: Planner Node
# ============================================================================
def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Planner Agent : asks the LLM for 3 topical tags and a ≤25-word summary.
    On revision rounds it includes the Reviewer's feedback in the prompt.
    """
    print("\n" + "=" * 60)
    print("NODE: Planner")
    print("=" * 60)

    title   = state["title"]
    content = state["content"]
    llm     = state["llm"]

    # If the Reviewer flagged issues, include them so the Planner can fix
    feedback = state.get("reviewer_feedback", {})
    feedback_section = ""
    if feedback and feedback.get("has_issues"):
        feedback_section = (
            "\n\nThe Reviewer found problems with your previous answer. "
            f"Fix these issues:\n{feedback.get('issues', '')}"
        )

    prompt = f"""Analyze this blog post. Return ONLY a JSON object — no other text.

Blog Title: {title}
Blog Content: {content}
{feedback_section}

Return this exact JSON format:
{{"tags": ["tag1", "tag2", "tag3"], "summary": "one sentence, max 25 words"}}"""

    # Call the LLM
    response = llm.invoke(prompt)
    response_text = response.content if hasattr(response, "content") else str(response)

    print(f"\nPlanner raw LLM output:\n{response_text}")

    # Parse (with fallback)
    try:
        proposal = extract_json_from_text(response_text)

        # Validate / normalise
        if "tags" not in proposal or "summary" not in proposal:
            raise ValueError("Missing 'tags' or 'summary' key")
        if not isinstance(proposal["tags"], list):
            raise ValueError("'tags' is not a list")
        # Ensure exactly 3 tags
        proposal["tags"] = proposal["tags"][:3]
        while len(proposal["tags"]) < 3:
            proposal["tags"].append("general")
        # Trim summary if over 25 words
        words = proposal["summary"].split()
        if len(words) > 25:
            proposal["summary"] = " ".join(words[:25])

        print(f"\nPlanner Proposal:")
        print(f"   Tags   : {proposal['tags']}")
        print(f"   Summary: {proposal['summary']}")
        print(f"   Words  : {len(proposal['summary'].split())}")

    except Exception as e:
        print(f"\nParse error: {e}")
        proposal = {
            "tags": ["tag1", "tag2", "tag3"],
            "summary": "one word summary"
        }
        print(f"   Using fallback proposal: {proposal}")

    return {"planner_proposal": proposal}


# ============================================================================
# STEP 3: Reviewer Node
# ============================================================================
def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """
    Reviewer Agent : validates the Planner output:
      1. Exactly 3 tags
      2. Summary ≤ 25 words
      3. Tags are topically relevant (LLM check)
    """
    print("\n" + "=" * 60)
    print("NODE: Reviewer")
    print("=" * 60)

    proposal = state.get("planner_proposal", {})
    content  = state["content"]
    llm      = state["llm"]

    if not proposal:
        return {"reviewer_feedback": {"has_issues": True,
                                       "issues": "No proposal received from Planner."}}

    tags    = proposal.get("tags", [])
    summary = proposal.get("summary", "")

    print(f"\nReviewing proposal:")
    print(f"   Tags   : {tags}")
    print(f"   Summary: {summary}")

    issues = []

    # Rule 1 – exactly 3 tags
    if len(tags) != 3:
        issues.append(f"Need exactly 3 tags (got {len(tags)})")

    # Rule 2 – summary ≤ 25 words
    word_count = len(summary.split())
    if word_count > 25:
        issues.append(f"Summary too long ({word_count} words, max 25)")

    # Rule 3 – no empty tags
    if any(not t or not t.strip() for t in tags):
        issues.append("One or more tags are empty")

    # Rule 4 – summary not empty
    if not summary.strip():
        issues.append("Summary is empty")

    # Rule 5 – LLM semantic relevance check
    check_prompt = (
        f"Are these tags relevant to the content? "
        f"Tags: {tags}. Content: {content[:200]}. "
        f"Answer only YES or NO."
    )
    resp = llm.invoke(check_prompt)
    semantic = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()

    # --- TEST: Force modification loop? ---
    # To test the loop, we can force an issue here:
    # force_issue = True  # <--- TOGGLE THIS TO TEST LOOP
    force_issue = True 

    if force_issue:
        issues.append("FORCED TEST ISSUE: Please revise the tags to be more specific.")

    # Build feedback
    if issues:
        feedback = {"has_issues": True, "issues": "; ".join(issues)}
        print(f"\nIssues: {feedback['issues']}")
    else:
        feedback = {"has_issues": False, "issues": None}
        print("\nProposal APPROVED — no issues found.")

    return {"reviewer_feedback": feedback}


# ============================================================================
# STEP 4: Supervisor Node
# ============================================================================
def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """Supervisor increments the turn counter."""
    new_turn = state.get("turn_count", 0) + 1
    print(f"\nSupervisor: Turn {new_turn}")
    return {"turn_count": new_turn}


# ============================================================================
# STEP 5: Router Logic (conditional edges)
# ============================================================================
def router_logic(state: AgentState) -> Literal["planner", "reviewer", "__end__"]:
    """
    Decides where to go next:
      • No proposal yet          → planner
      • Proposal but no review   → reviewer
      • Review found issues      → planner  (loop back for revision)
      • Review passed            → END
      • Turn limit (5) reached   → END  (safety stop)
    """
    MAX_TURNS = 5

    turn     = state.get("turn_count", 0)
    proposal = state.get("planner_proposal")
    feedback = state.get("reviewer_feedback")

    print(f"\nRouter (turn {turn}):")
    print(f"proposal={bool(proposal)}  feedback={bool(feedback)}")

    if turn >= MAX_TURNS:
        print("Max turns → END")
        return END

    if not proposal:
        print("   → PLANNER (no proposal yet)")
        return "planner"

    if not feedback:
        print("   → REVIEWER (need review)")
        return "reviewer"

    if feedback.get("has_issues"):
        print("   → PLANNER (revision needed)")
        return "planner"

    print("   → END (approved)")
    return END


# ============================================================================
# STEP 6: Build the Graph
# ============================================================================
def create_agent_graph():
    """Assemble the StateGraph and compile it."""
    print("\nBuilding Agent Graph...")

    workflow = StateGraph(AgentState)

    # --- nodes ---
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("planner",    planner_node)
    workflow.add_node("reviewer",   reviewer_node)

    # --- entry point ---
    workflow.set_entry_point("supervisor")

    # --- edges ---
    workflow.add_conditional_edges(
        "supervisor",
        router_logic,
        {"planner": "planner", "reviewer": "reviewer", END: END},
    )
    workflow.add_edge("planner",  "supervisor")   # after planning → supervisor
    workflow.add_edge("reviewer", "supervisor")   # after review   → supervisor

    app = workflow.compile()
    print("Graph compiled!\n")
    return app


# ============================================================================
# STEP 7: Main — run everything
# ============================================================================
def main():
    print("\n" + "=" * 15)
    print("STATEFUL AGENT GRAPH — BLOG TAG & SUMMARY GENERATOR")
    print("=" * 15)

    # --- LLM setup ---
    print("\nConnecting to Ollama (llama3) ...")
    llm = ChatOllama(model="llama3", temperature=0.7)
    print("LLM ready")

    # --- Blog input ---
    blog_title = "Building Robust MLOps Pipelines with Continuous Model Monitoring"
    blog_content = """Machine learning models in production face unique challenges that traditional
                      software doesn't encounter. Data drift, concept drift, and model degradation can 
                      silently reduce accuracy over time. Implementing continuous monitoring is essential 
                      for maintaining ML system reliability. Modern MLOps practices emphasize automated 
                      retraining pipelines, feature store management, and real-time performance tracking.
                      Tools like MLflow, Kubeflow, and custom observability platforms help teams detect anomalies early. 
                      By establishing baseline metrics, setting up alerting thresholds, and creating automated rollback 
                      mechanisms, organizations can ensure their models remain accurate and trustworthy in production 
                      environments."""

    print(f"\nInput blog:")
    print(f"   Title  : {blog_title}")
    print(f"   Content: {blog_content[:100]}...")

    # --- Initial state ---
    initial_state: AgentState = {
        "title": blog_title,
        "content": blog_content,
        "task": "Generate exactly 3 topical tags and a ≤25-word summary",
        "llm": llm,
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
    }

    # --- Build & run the graph ---
    app = create_agent_graph()

    print("=" * 15)
    print("EXECUTING GRAPH")
    print("=" * 15)

    # Use .stream() to see steps, but capture final state correctly
    final_state = initial_state
    for step_output in app.stream(initial_state):
        # step_output is like {'planner': {'planner_proposal': ...}}
        # We need to update our local 'final_state' with these changes
        for node_name, updates in step_output.items():
            final_state.update(updates)
            print(f"   -- Step completed: {node_name} --")

    # --- Print results ---
    print("\n" + "=" * 15)
    print("FINAL RESULTS")
    print("=" * 15)

    proposal = final_state.get("planner_proposal", {})
    feedback = final_state.get("reviewer_feedback", {})

    # Build the final publish JSON
    final_json = {
        "title": final_state["title"],
        "tags": proposal.get("tags", []),
        "summary": proposal.get("summary", ""),
        "metadata": {
            "total_turns": final_state.get("turn_count", 0),
            "review_status": "approved" if not feedback.get("has_issues") else "needs_revision",
        },
    }

    print("\nFinal Publish JSON:")
    print(json.dumps(final_json, indent=2))
    if feedback.get("has_issues"):
        print(f"YES — issues found: {feedback['issues']}")
        print("The Planner was sent back to revise its output.")
    else:
        print("NO — the Reviewer approved the proposal without changes.")


if __name__ == "__main__":
    main()
