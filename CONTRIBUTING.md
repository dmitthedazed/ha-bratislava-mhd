# Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest -q
```

GitHub Actions runs the same checks on every push and pull request, plus hassfest and
the HACS validator.

## Local Home Assistant

`docker-compose.yml` starts Home Assistant in Docker on port 8124. Its config lives in
`.ha-config/` (ignored by git), and `custom_components/bratislava_mhd` is bind-mounted, so
code changes show up without copying anything.

```bash
docker compose up -d              # start, http://localhost:8124
docker compose logs -f            # logs
docker compose restart            # after changes to manifest.json, const.py or the card URL
docker compose down               # stop
```

1. The first time, open http://localhost:8124 and create a user. For debug logs, add to
   `.ha-config/configuration.yaml`:

   ```yaml
   logger:
     logs:
       custom_components.bratislava_mhd: debug
   ```

2. **Settings → Devices & services → Add integration → Bratislava MHD**.
3. After Python changes: **Devices & services → Bratislava MHD → ⋮ → Reload**.

## The card

`custom_components/bratislava_mhd/www/bratislava-mhd-card.js` is plain JavaScript, no build
step. Edit it and hard-refresh the dashboard (Ctrl+F5). The integration serves it with the
manifest version in the URL, so bump `version` in `manifest.json` when you release a card
change, or browsers keep the old file.

## Releases

Bump `version` in `manifest.json`, then tag `vX.Y.Z` and publish a GitHub release; HACS
offers releases to users.
