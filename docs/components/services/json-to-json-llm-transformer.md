# JSON To JSON LLM Transformer

## Purpose

`json-to-json-llm-transformer` is the first generic LLM-backed LinkSmith service.

It exists to turn a structured JSON input into a different structured JSON output while still fitting the LinkSmith service contract model:

- explicit file inputs
- explicit file output
- container-first execution
- deterministic output validation after a non-deterministic model call

## Contract

Inputs:

- `data`: source JSON document
- `prompt`: Mustache prompt template
- `schema`: JSON Schema document describing the required output

Output:

- `result`: transformed JSON document

## How It Works

1. Load the source JSON, prompt template, and output schema from disk.
2. Render the prompt template with:
   - `input`
   - `output_schema`
   - `output_schema_json`
3. Call an OpenAI-compatible `/chat/completions` endpoint.
4. Extract the first valid JSON object from the model response.
5. Validate that object against the provided schema.
6. Retry with a repair message if the model returns invalid JSON or schema-mismatched JSON.
7. Write the validated JSON result to disk.

## Configuration

The service accepts LLM runtime settings through CLI arguments, with env defaults for local use:

- `--base-url` or `LINKSMITH_LLM_BASE_URL`
- `--api-key` or `LINKSMITH_LLM_API_KEY`
- `--model` or `LINKSMITH_LLM_MODEL`
- `--temperature` or `LINKSMITH_LLM_TEMPERATURE`
- `--max-retries` or `LINKSMITH_LLM_MAX_RETRIES`
- `--timeout-seconds` or `LINKSMITH_LLM_TIMEOUT_SECONDS`

## Why This Shape

This keeps the first LLM slice narrow:

- one JSON input
- one prompt file
- one schema file
- one JSON output

That is enough to test the hardest part of the pipeline system now: forcing a probabilistic model behind a deterministic file contract.

## Core Reflection

`linksmith-core` helped with:

- loading typed JSON and text artifacts
- contract validation around inputs and outputs
- writing the final JSON artifact to the expected output directory

Current friction:

- output schema validation can happen in `linksmith-core`, but the LLM service still needs the schema contents as an explicit input so it can instruct the model
- engine runtime config currently passes static CLI args more naturally than dynamic per-service env vars
