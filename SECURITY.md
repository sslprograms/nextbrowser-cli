# Security

## Never commit

- `.env` or any file with real passwords, API keys, or MLX tokens
- `~/.nextbrowser/multilogin_tokens.yaml` (local only; already in `.gitignore` patterns)
- Screenshots or logs from automation runs (`pixelscan-*.png`, `nb-test-*.png`, etc.)
- Personal Multilogin folder/profile UUIDs in docs or examples

Use `.env.example` as the template. Copy to `.env` locally and keep `.env` out of git.

## Setup

```bash
cp .env.example .env   # Linux/macOS
# edit .env with your values — never push .env
```

MLX passwords are prompted at sign-in (`getpass`) and are **not** written to disk by this harness.

## Reporting

Open a private issue on GitHub if you find a security problem in this repository.
