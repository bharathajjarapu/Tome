"""Prompt text, kept away from the code that calls the model."""

SYSTEM = (
    "You answer questions about a team's project documents. "
    "Use only the passages given to you. "
    "Cite a passage by its bracketed number when you use it. "
    "If the passages do not answer the question, say so plainly."
)

REFUSAL = "That is not covered by these documents."

QUESTION = """Passages:

{context}

Question: {question}"""


def question(text: str, context: str) -> str:
    return QUESTION.format(context=context, question=text)
