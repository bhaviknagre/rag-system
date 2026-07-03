import argparse
import json
import logging
from pathlib import Path
from src.pipeline import ingest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest documents into vector store")
    parser.add_argument("--provider", default=None,
                        choices=["chroma", "pinecone", "mongodb"],
                        help="Vector DB backend (default: from .env)")
    parser.add_argument("--strategy", default=None,
                        choices=["recursive", "semantic", "sentence_window"],
                        help="Chunking strategy (default: from .env)")
    parser.add_argument("--raw-dir", default="data/raw",
                        help="Directory containing raw documents")
    parser.add_argument("--reset", default="true",
                        help="Reset vector store before ingesting (true/false)")
    return parser.parse_args()


def main():
    args = parse_args()
    reset = args.reset.lower() in ("true", "1", "yes")

    logger.info(
        f"Starting ingestion | provider={args.provider} | "
        f"strategy={args.strategy} | reset={reset}"
    )

    summary = ingest(
        raw_dir=args.raw_dir,
        provider=args.provider,
        strategy=args.strategy,
        reset=reset
    )

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "ingestion_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Summary written to {summary_path}")
    metrics = {
        "documents_loaded": summary.get("documents_loaded", 0),
        "chunks_created": summary.get("chunks_created", 0),
        "chunks_added": summary.get("chunks_added", 0),
        "total_chunks_in_store": summary.get("total_chunks_in_store", 0)
    }
    metrics_path = out_dir / "ingestion_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Metrics written to {metrics_path}")

    print("\n--- Ingestion Summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()