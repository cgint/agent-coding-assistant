#!/usr/bin/env python3
# /// script
# dependencies = [
#     "dspy-ai",
#     "mlflow",
#     "trafilatura",
#     "tavily-python",
#     "langchain-text-splitters"
# ]
# requires-python = ">=3.11"
# ///

import mlflow
mlflow.set_experiment("dspy_agent_coding_assistant")
mlflow.autolog()


if __name__ == "__main__":
    # Use the service for configuration and Q&A
    from dspy_agent_service import DspyAgentService
    import dspy
    service = DspyAgentService()
    
    # Define all questions upfront
    questions = [
        "What are the different add-ons available for Campaign Orchestrator and what do they include?",
        "How do I setup PMax campaigns with page feeds?",
        "What are the latest Google Ads feature updates announced in January 2025?"
    ]
    
    # Store results for markdown output
    results = []
    
    # Initialize conversation history (None for first call)
    conversation_history = None
    
    # Process each question in a loop, maintaining history
    with mlflow.start_run():
        for i, question in enumerate(questions, 1):
            print(f"\n--- User Question {i} ---\n{question}\n")
            
            # Call the new method with history
            response = service.answer_question_with_history(question, conversation_history)
            
            # Extract history from response for next iteration
            conversation_history = dspy.History(messages=response.history["messages"])
            
            # Store result for markdown
            results.append({
                'question': response.question,
                'answer': response.final_answer,
                'tracked_usage_metadata': response.tracked_usage_metadata
            })

    # Write all questions and answers to run.md
    print("\n--- Writing results to run.md ---")
    
    markdown_content = "# DSPy Agent Results\n\n"
    for i, result in enumerate(results, 1):
        markdown_content += f"""## Question {i}
**Question:** {result['question']}

**Answer:**
{result['answer']}

**Tracked usage metadata:**
{result['tracked_usage_metadata']}

---
"""
    
    try:
        with open("run.md", "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print("✅ Successfully wrote results to run.md")
    except Exception as e:
        print(f"❌ Error writing to run.md: {e}")