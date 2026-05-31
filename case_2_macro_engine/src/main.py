from macro_analyzer import analyze_macro_scenario
from report_generator import generate_report
from utils import save_json, save_text


def load_scenario(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


scenario = load_scenario(
    "case_2_macro_engine/data/scenario.txt"
)

analysis = analyze_macro_scenario(scenario)

save_json(
    analysis,
    "case_2_macro_engine/outputs/analysis.json"
)

report = generate_report(analysis)

save_text(
    report,
    "case_2_macro_engine/outputs/report.md"
)

print("Macro analysis completed successfully.")