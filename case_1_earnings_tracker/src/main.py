from parser import load_transcript, split_text_into_chunks
from analyzer import analyze_transcript, combine_chunk_analyses
from report_generator import generate_report
from utils import save_json, save_text

transcript = load_transcript(
    "case_1_earnings_tracker/data/sample_transcript.txt"
)

chunks = split_text_into_chunks(transcript, chunk_size=100)

chunk_analyses = []

for chunk in chunks:
    analysis = analyze_transcript(chunk)
    chunk_analyses.append(analysis)

final_analysis = combine_chunk_analyses(chunk_analyses)

save_json(
    final_analysis,
    "case_1_earnings_tracker/outputs/analysis.json"
)

report = generate_report(final_analysis)

save_text(
    report,
    "case_1_earnings_tracker/outputs/report.md"
)

print("Final analysis saved successfully.")