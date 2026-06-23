# Anchises Stock QA Marketplace

This repository is a Codex marketplace root for the Anchises Stock QA plugin.
Its marketplace manifest lives at `.agents/plugins/marketplace.json` and points
to the plugin package at `plugins/anchises-stock-qa`.

Anchises Stock QA is a Codex plugin for asking questions about stock market
data.

Codex writes safe read-only SQL, the plugin exports the result to a local CSV,
and Codex then uses pandas to analyze the CSV and answer your question.

Users do not need a database URL. Access is provided through the Anchises Stock
QA API URL and your personal API token.

## What You Need

- Codex with plugin support.
- Python 3 on your machine.
- Your Anchises Stock QA API token.

## Install

Add this repository URL as a Codex marketplace URL, then install
**Anchises Stock QA** from the Anchises-Tech marketplace.

If you are updating an existing install, refresh or re-add the same marketplace
URL and install the latest plugin version.

After installing or updating, open a new Codex thread so Codex can load the
latest plugin tools and instructions.

Then ask Codex:

```text
Set up Anchises Stock QA
```

Codex will show a Terminal command that matches your installed plugin path.

## Configure Database Access

The plugin connects through the Anchises Stock QA API:

```text
https://anchisesdata.com/anchises-stock-qa
```

The easiest setup path is to ask Codex:

```text
Set up Anchises Stock QA
```

Codex will return a command like this:

```bash
bash "/Users/you/.codex/plugins/cache/.../anchises-stock-qa/.../scripts/init_config.sh" --prepare-runtime
```

Run that command in Terminal. The script will ask for your API token and hide it
while you type. The first run may take a few minutes because it prepares the
plugin Python runtime and installs dependencies such as pandas into the plugin
`.venv`.

The config is saved here:

```text
~/.config/anchises-stock-qa/config.toml
```

Keep this file private because it contains your API token.

To replace your API token later, ask Codex again:

```text
Set up Anchises Stock QA
```

The same command updates the token and keeps your other settings. Use the force
command only if you want to rebuild the whole config from defaults.

## Example Config

```toml
[backend]
mode = "remote_api"
api_base_url = "https://anchisesdata.com/anchises-stock-qa"
api_token = "paste_your_api_token_here"

[database]
url = ""
access_mode = "readonly"

[outputs]
dir = "~/.local/share/anchises-stock-qa/outputs"
cleanup_enabled = true
cleanup_interval_days = 7
retention_days = 30

[prompts]
override_dir = ""

[exchanges.aliases]
# Optional aliases for exchange codes discovered from database table names.
# "London" = "lse"
```

You normally only need to fill in `api_token`.

## Check That It Works

In Codex, ask:

```text
Check the Anchises Stock QA connection.
```

You can also run this from the plugin folder:

```bash
cd plugins/anchises-stock-qa
python3 scripts/ask_stock.py --verify-db
```

## How To Use It

Ask stock questions naturally in Codex, for example:

```text
Find the strongest momentum stocks from the latest data.
```

```text
Which mining stocks had unusual volume recently?
```

```text
Show the best performers over the past month.
```

The plugin discovers available exchanges from the remote data service, so new
exchanges can be added without editing the prompt files.

## Outputs

Query results are saved as CSV files under the output directory in your config.
By default:

```text
~/.local/share/anchises-stock-qa/outputs
```

Old output folders are cleaned automatically when the plugin runs. By default,
cleanup checks once every 7 days and removes plugin-generated runs older than 30
days.

## Custom Prompts

You can override the built-in prompts without editing the plugin:

```bash
mkdir -p ~/.config/anchises-stock-qa/prompts
cp plugins/anchises-stock-qa/prompts/*.md ~/.config/anchises-stock-qa/prompts/
```

Then set this in `config.toml`:

```toml
[prompts]
override_dir = "~/.config/anchises-stock-qa/prompts"
```

You only need to copy the prompt files you want to customize. Missing files fall
back to the plugin defaults.

## Updating Or Reinstalling

Your local config file is not part of the plugin install. Updating, removing, or
reinstalling the plugin will not delete:

```text
~/.config/anchises-stock-qa/config.toml
```

You only need to configure again if you delete that file or receive a new API
token.

## Safety

- Users do not receive the database URL.
- The plugin only accepts safe read-only queries.
- API tokens are redacted in plugin output and metadata.
- The database remains behind the remote API service.
