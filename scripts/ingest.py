import argparse
from src.pipeline import raw_ingest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_dir", default="data/raw")
    parser.add_argument("--reset", action="store_true")

    args = parser.parse_args()

    print("\n========== STARTING INGESTION ==========\n")

    try:
        result = raw_ingest(
            raw_dir=args.raw_dir,
            reset=args.reset
        )

        print("\n========== INGESTION RESULT ==========\n")

        for k, v in result.items():
            print(f"{k}: {v}")

        print("\n========== DONE ==========\n")

    except Exception as e:
        print("\n INGESTION FAILED:")
        print(str(e))
        raise


if __name__ == "__main__":
    main()