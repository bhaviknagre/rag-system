import requests

from src.config import settings
from src.retrieval.retriever import get_retriever

PROMPT_TEMPLATE = """
You are a helpful assistant.

Answer the user's question using ONLY the provided context.

If the user asks for a summary, summarize the context.

If the answer cannot be determined from the context, respond exactly:

I don't know.

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

