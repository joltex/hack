# speedread

Wrapper to summarize PDFs and other documents using LLMs.


## Authentication

You can supply your API key directly when instantiating an `AiReader` or they will be automatically fetched from the `ANTHROPIC_API_KEY` and/or `OPEN_AI_API_KEY` environment variables depending on the model selected.

## Other

You may need to install `poppler` in order to parse image-based PDFs.

```bash

brew install poppler
```