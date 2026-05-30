def load_transcript(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def load_prompt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def split_text_into_chunks(text, chunk_size=500):
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) <= chunk_size:
            current_chunk += paragraph + "\n\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks