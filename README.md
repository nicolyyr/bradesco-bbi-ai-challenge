## Architecture

The solution follows a modular pipeline architecture:

* `parser.py`: transcript ingestion and chunking
* `analyzer.py`: sentiment analysis, guidance extraction, red flag detection, and structured insight generation
* `report_generator.py`: markdown report generation
* `utils.py`: output persistence
* `main.py`: pipeline orchestration

## Prompt Engineering Decisions

The analysis prompt was designed to encourage structured outputs and reduce ambiguity.

Key decisions:

* Explicit JSON schema definition
* Separation between transcript content and instructions
* Requirement for evidence-based conclusions
* Emphasis on concise executive summaries

## Time Spent

Approximate time spent:

* Case 1: ~12 hours

## Prioritization Rationale

The focus was placed on building a reliable end-to-end pipeline for earnings call analysis before implementing advanced features.

Priority was given to:

* modular architecture
* explainable outputs
* structured reporting

rather than adding complex optional extensions.

## Main Limitations

1. The current implementation uses rule-based sentiment analysis rather than a production-grade LLM.
2. Comparison against previous quarters is not yet automated due to the absence of historical transcripts.
3. Analyst question extraction currently requires transcripts containing a dedicated Q&A section.

## What I Would Add With Two More Weeks

* Integration with GPT/Claude for deeper contextual reasoning
* Automated comparison against previous earnings calls
* Analyst Q&A extraction and response quality scoring
* Citation tracking for every generated insight
* Streamlit interface for interactive exploration
