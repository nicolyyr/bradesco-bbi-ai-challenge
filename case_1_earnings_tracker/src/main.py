from parser import (
    load_transcript,
    split_text_into_chunks,
    load_prompt
)

from analyzer import build_analysis_request

transcript = load_transcript(
    "case_1_earnings_tracker/data/sample_transcript.txt"
)

prompt = load_prompt(
    "case_1_earnings_tracker/prompts/analysis_prompt.txt"
)

chunks = split_text_into_chunks(
    transcript,
    chunk_size=100
)

request = build_analysis_request(
    prompt,
    chunks[0]
)

print(request)