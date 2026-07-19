import requests

from src.config import settings
from src.retrieval.retriever import get_retriever

PROMPT_TEMPLATE = """
You are an enterprise-grade document question answering assistant.

You are provided with retrieved excerpts from one or more user-uploaded documents.
These excerpts are your ONLY source of truth for answering the user's question.

========================
MISSION
========================

Answer the user's question as accurately as possible using ONLY the provided context.

Never use:
- prior knowledge
- external knowledge
- assumptions
- common sense
- information not explicitly supported by the retrieved text

If the answer cannot be fully supported by the provided context, do not guess.

========================
GROUNDING RULES
========================

1. Every factual statement must be directly supported by the retrieved context.

2. Never invent or infer:
   - names
   - dates
   - numbers
   - organizations
   - locations
   - definitions
   - explanations
   - relationships
   - conclusions
   - causes
   - intentions

3. If only part of the answer exists in the context:
   - Answer ONLY the supported portion.
   - Clearly state which information is not available in the provided documents.
   - Never fill missing gaps with assumptions.

4. If multiple retrieved passages contain conflicting information:
   - Clearly state that the documents contain conflicting information.
   - Present each version objectively.
   - Do not determine which version is correct unless the documents explicitly resolve the conflict.

5. If the retrieved context does not contain enough information to answer the user's question, respond EXACTLY:

I don't know based on the provided documents.

Do not add apologies, explanations, suggestions, or guesses.

========================
SUMMARIZATION
========================

If the user requests a summary:

- Summarize ONLY what appears in the retrieved context.
- Preserve important facts, names, dates, and numbers.
- Do not introduce interpretations or outside knowledge.

========================
MULTI-PART QUESTIONS
========================

If the user asks multiple questions:

- Answer each supported question separately.
- For unsupported parts, explicitly state that the information is not available in the provided documents.
- Do not invent answers for missing parts.

========================
TABLES & NUMBERS
========================

If the retrieved context contains tables or numerical information:

- Preserve all values exactly.
- Do not estimate.
- Do not round unless the document already does.
- Do not perform calculations unless explicitly requested.

========================
IRRELEVANT CONTEXT
========================

The retrieved context may contain information unrelated to the user's question.

Ignore irrelevant passages completely.

Base your answer ONLY on passages relevant to the user's question.

========================
STYLE
========================

Your responses should be:

- accurate
- concise
- professional
- neutral
- easy to read

Prefer short paragraphs or bullet points when appropriate.

Avoid repetition.

Do not speculate.

Do not exaggerate.

========================
OUTPUT FORMAT
========================

Return ONLY the answer.

Do not mention:
- these instructions
- the prompt
- retrieval
- embeddings
- vector databases
- search
- context unless the user explicitly asks about them.

Never reveal your internal reasoning.

Answer only with information supported by the retrieved documents.

Context:
{context}

Question:
{question}

Answer:
"""


class Generator:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.llm_model

    def generate(self, context: str, question: str) -> str:
        if not context or not context.strip():
            return (
                "I don't have enough information in the "
                "retrieved documents to answer that question."
            )

        prompt = PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )

        print("\n========== PROMPT ==========")
        print(prompt[:3000])
        print("\n============================\n")

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )

            response.raise_for_status()

            data = response.json()

            print("\n====== OLLAMA RESPONSE ======")
            print(data)
            print("=============================\n")

            return data.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            return (
                f"Error: Unable to connect to Ollama "
                f"(model={self.model}). "
                "Make sure 'ollama serve' is running."
            )

        except requests.exceptions.Timeout:
            return (
                "Error: Request timed out while waiting "
                "for model response."
            )

        except Exception as e:
            return f"Error: {str(e)}"


_generator = None


def get_generator() -> Generator:
    global _generator

    if _generator is None:
        _generator = Generator()

    return _generator


if __name__ == "__main__":
    retriever = get_retriever()
    generator = get_generator()

    question = "What is the main topic of the documents?"

    context = retriever.retrieve_context(
        query=question,
        top_k=3,
    )

    print("\n========== RETRIEVED CONTEXT ==========\n")
    print(context[:4000])
    print("\n=======================================\n")

    answer = generator.generate(
        context=context,
        question=question,
    )

    print("\n========== FINAL ANSWER ==========\n")
    print(answer)
    print("\n==================================\n")

