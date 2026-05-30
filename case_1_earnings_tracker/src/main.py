from parser import load_transcript
from analyzer import analyze_transcript
from report_generator import generate_report
from utils import save_json, save_text

transcript = load_transcript(
    "case_1_earnings_tracker/data/sample_transcript.txt"
)

analysis = analyze_transcript(transcript)

save_json(
    analysis,
    "case_1_earnings_tracker/outputs/analysis.json"
)

report = generate_report(analysis)

save_text(
    report,
    "case_1_earnings_tracker/outputs/report.md"
)

print("Analysis saved successfully.")