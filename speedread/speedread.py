import logging
from pathlib import Path

import anthropic
import attrs
import pdf2image
import pytesseract
from pypdf import PdfReader

import config

AiClient = anthropic.Anthropic

# configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
logger.addHandler(handler)


@attrs.define(auto_attribs=True)
class AiReader:
    file: str | Path | None = None
    model: str = "claude-3-opus-20240229"
    text: str | None = None
    client: AiClient = attrs.field(init=False)
    api_key: str | None = None

    def __attrs_post_init__(self):
        if self.file and not self.text:
            self.text = read_file(self.file)

        if "claude" in self.model:
            self.api_key = self.api_key or config.ANTHROPIC_API_KEY
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            raise NotImplementedError(f"Model {self.model} not supported")

    def summarize(
        self, prompt: str = "Please summarize the text.", max_tokens: int = 2048
    ) -> str:
        return summarize_text(self.text, prompt, self.client, self.model, max_tokens)


def get_response(
    prompt: str,
    client: anthropic.Anthropic,
    model: str = "claude-3-opus-20240229",
    max_tokens: int = 2048,
) -> str:
    return (
        client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        .content[0]
        .text
    )


def read_file(file: str | Path) -> str:
    if not file:
        raise ValueError("No file path provided")
    if file.endswith(".pdf"):
        logger.info(f"Reading pdf file...")
        reader = PdfReader(file)
        text = "".join([page.extract_text() for page in reader.pages])
        if not text:
            logger.info("No text found in pdf, attempting to extract from images...")
            text = text_from_images(file)
    elif file.endswith(".txt"):
        logger.info(f"Reading txt file...")
        with open(file, "r") as f:
            text = f.read()
    else:
        raise NotImplementedError(f"File type {file.split('.')[-1]} not supported")

    return text


def summarize_text(
    text: str, prompt: str, client: AiClient, model: str, max_tokens: int
) -> str:
    full_prompt = f"Here is the contents of a pdf <content>{text}</content>"
    full_prompt += f"/n{prompt}"
    return get_response(full_prompt, client, model, max_tokens)


def text_from_images(file: str | Path) -> str:
    images = pdf2image.convert_from_path(file)
    text = ""
    for image in images:
        text += pytesseract.image_to_string(image)
    return text
