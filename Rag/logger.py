import csv
from datetime import datetime
import os

LOG_FILE = "similarity_logs.csv"

def log_similarity(question, docs_with_scores):
    """
    Logs similarity search results to a CSV file
    """
    file_exists = os.path.isfile(LOG_FILE)

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header only once
        if not file_exists:
            writer.writerow([
                "timestamp",
                "question",
                "score",
                "file_name",
                "page",
                "text_preview"
            ])

        for rank, (doc, score) in enumerate(docs_with_scores, start=1):
            writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            question,
            rank,
            round(score, 4),
            doc.metadata.get("file_name"),
            doc.metadata.get("page"),
            doc.page_content[:80].replace("\n", " ")
        ])
