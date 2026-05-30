import json


def save_json(data, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def save_text(content, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)