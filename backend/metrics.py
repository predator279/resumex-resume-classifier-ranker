"""
metrics.py — Prometheus metrics definitions for ResumeX.

Provides custom instrumentation for:
  - BERT classification inference latency
  - ATS ranking latency
  - Job description parsing latency
  - Classifier confidence score distribution (data drift indicator)
  - Resume throughput counter
  - Uploaded resume file size distribution
"""

from prometheus_client import Counter, Histogram

# ---------------------------------------------------------------------------
# ML Inference & Processing Latencies (in seconds)
# ---------------------------------------------------------------------------

BERT_INFERENCE_DURATION = Histogram(
    "bert_inference_duration_seconds",
    "Time taken for BERT resume classification inference in seconds",
    buckets=[0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0],
)

ATS_RANKING_DURATION = Histogram(
    "ats_ranking_duration_seconds",
    "Time taken for 5-dimension ATS candidate ranking in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0],
)

JD_PARSER_DURATION = Histogram(
    "jd_parser_duration_seconds",
    "Time taken to parse job description requirements in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)

# ---------------------------------------------------------------------------
# Model Quality & Data Drift Proxies
# ---------------------------------------------------------------------------

CLASSIFIER_CONFIDENCE = Histogram(
    "classifier_confidence_scores",
    "Distribution of top-1 classification confidence scores (proxy for out-of-domain drift)",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)

# ---------------------------------------------------------------------------
# Throughput & Payload Volume
# ---------------------------------------------------------------------------

RESUMES_PROCESSED_TOTAL = Counter(
    "resumes_processed_total",
    "Total count of resumes parsed and processed",
    ["endpoint", "status"],
)

RESUME_FILE_SIZE_BYTES = Histogram(
    "resume_file_size_bytes",
    "Distribution of uploaded resume file sizes in bytes",
    buckets=[10_240, 51_200, 102_400, 524_288, 1_048_576, 2_097_152, 5_242_880, 10_485_760],
)
