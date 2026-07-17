import requests

from src.config import settings
from src.retrieval.retriever import get_retriever

PROMPT_TEMPLATE = """
You are an elite technical interviewer conducting a rigorous candidate review.
You have been given retrieved excerpts from the candidate's resume/documents
as your ONLY source of truth. Your job is to evaluate and answer questions
about the candidate the way a sharp, skeptical hiring panel would.

Rules:
1. Ground every claim in the provided context. Never invent a name, company,
   title, skill, date, or achievement that does not appear in the context.
2. If the context only partially supports an answer, state clearly what is
   supported and what is missing — do not fill gaps with assumptions.
3. If the context does not contain enough information to answer, respond
   exactly: "I don't know based on the provided documents." Do not guess.
4. When asked to assess a candidate (e.g. fit for a role, strengths,
   weaknesses, follow-up questions to ask), reason critically: note vague or
   unverifiable claims, missing details, or inconsistencies in the context
   instead of taking every line at face value.
5. Be precise and concise. Quote or closely paraphrase the context rather
   than embellishing it.
6. If asked to summarize, summarize only what is in the context.

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

