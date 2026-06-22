# Anchises Stock QA

Anchises Stock QA is a Codex plugin for asking questions about a local
`Stocks_Tracker` MySQL database.

Codex writes safe read-only SQL, the plugin exports the result to CSV, and
Codex then uses pandas to analyze the CSV and answer your question.

The plugin does not include a database connection. Each user configures their
own read-only database URL after installing the plugin.

## What You Need

- Codex with plugin support.
- Python 3 on your machine.
- Access to a MySQL `Stocks_Tracker` database.
- A read-only MySQL account.

## Install

Open the shared plugin link in the Codex app and click **Install**.

If you are updating an existing install, open the same plugin link again and
install the latest version.

After installing or updating, open a new Codex thread so Codex can load the
latest plugin tools and instructions.

## Configure The Database

Open Terminal, switch to the plugin folder, then create the local config file:

```bash
cd <path-to-anchises-stock-qa>
bash scripts/init_config.sh
```

For example, if you downloaded the plugin to `~/Downloads`:

```bash
cd ~/Downloads/anchises-stock-qa
bash scripts/init_config.sh
```

The script will ask for your read-only MySQL URL. Example:

```text
mysql+pymysql://stock_reader:password@127.0.0.1:3306/Stocks_Tracker?charset=utf8mb4
```

The config is saved here:

```text
~/.config/anchises-stock-qa/config.toml
```

Keep this file private. It contains your database URL.

## Example Config

```toml
[database]
url = "mysql+pymysql://stock_reader:password@127.0.0.1:3306/Stocks_Tracker?charset=utf8mb4"
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

The `access_mode` value must stay `"readonly"`.

## Database URL Examples

Local MySQL over TCP:

```text
mysql+pymysql://stock_reader:password@127.0.0.1:3306/Stocks_Tracker?charset=utf8mb4
```

Remote MySQL:

```text
mysql+pymysql://stock_reader:password@db.example.com:3306/Stocks_Tracker?charset=utf8mb4
```

Local MySQL socket:

```text
mysql+pymysql://stock_reader:password@localhost/Stocks_Tracker?unix_socket=/tmp/mysql.sock&charset=utf8mb4
```

## Check That It Works

In Codex, ask:

```text
Check the Anchises Stock QA database connection.
```

Or run:

```bash
python3 scripts/ask_stock.py --get-config
python3 scripts/ask_stock.py --verify-db
```

If you run the scripts directly from a clean source checkout, install the Python
dependencies first:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/ask_stock.py --verify-db
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

The plugin discovers available exchanges from your database table names, so new
exchanges can be added to the database without editing the prompt files.

## Outputs

Query results are saved as CSV files under the output directory in your config.
By default:

```text
~/.local/share/anchises-stock-qa/outputs
```

Old output folders are cleaned lazily when the plugin runs. By default, cleanup
checks once every 7 days and removes plugin-generated runs older than 30 days.

## Custom Prompts

You can override the built-in prompts without editing the plugin:

```bash
mkdir -p ~/.config/anchises-stock-qa/prompts
cp prompts/*.md ~/.config/anchises-stock-qa/prompts/
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

You only need to configure again if you delete that file or change your database
account.

## Safety

- The database account should be read-only.
- The plugin only accepts safe `SELECT` queries.
- Queries run in a read-only transaction.
- Database URLs are redacted in plugin output and metadata.
