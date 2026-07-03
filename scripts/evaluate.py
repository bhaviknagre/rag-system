import argparse
import json
import logging
from pathlib import Path
from src.vectorstore.store import query_store
from src.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = Settings()

TEST_QUERIES = [
    "What is this document about?",
    "What are the main topics discussed?",
    "What tools or technologies are mentioned?",
    "What are the key findings or conclusions?",
    "Who are the main stakeholders mentioned?"
]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality")
    parser.add_argument("--provider", default=None,
                        choices=["chroma", "pinecone", "mongodb"],
                        help="Vector DB backend to evaluate")
    parser.add_argument("--top-k", type=int, default=None,
                        help="Number of chunks to retrieve per query")
    return parser.parse_args()


def main():
    args = parse_args()
    provider = args.provider or settings.vector_db_provider
    top_k = args.top_k or settings.top_k

    logger.info(f"Evaluating | provider={provider} | top_k={top_k}")

    all_scores = []
    top1_scores = []
    queries_with_results = 0

    for query in TEST_QUERIES:
        try:
            results = query_store(query=query, top_k=top_k, provider=provider)
            if results:
                queries_with_results += 1
                scores = [r["score"] for r in results]
                top1_scores.append(scores[0])
                all_scores.extend(scores)
                logger.info(f"  Query: '{query[:50]}' | top1={scores[0]:.4f} | avg={sum(scores)/len(scores):.4f}")
            else:
                logger.warning(f"  Query: '{query[:50]}' | no results")
        except Exception as e:
            logger.error(f"  Query failed: '{query[:50]}' | {e}")

    metrics = {
        "provider": provider,
        "top_k": top_k,
        "total_queries": len(TEST_QUERIES),
        "queries_with_results": queries_with_results,
        "avg_top1_score": round(sum(top1_scores) / len(top1_scores), 4) if top1_scores else 0.0,
        "avg_top_k_score": round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0
    }

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = out_dir / "eval_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print("\n--- Evaluation Metrics ---")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    logger.info(f"Eval metrics written to {metrics_path}")


if __name__ == "__main__":
    main()