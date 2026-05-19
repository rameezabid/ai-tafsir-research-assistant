# Tafsir & Arabic Vocabulary Telegram Bot

A Telegram bot for Qur'anic tafsir and Arabic vocabulary research. The bot uses approved source layers only and answers from retrieved excerpts rather than open-ended web search.

It's just an assistant so it doesn't have memory or context to previous questions, so you can't have normal conversations like you would in chatGPT. It's designed only as a research assistant. So each message behaves like a new question.

The basic workflow is: ask question -> searches approved sources only -> sends results to AI for analysis -> sends analysis back + links to which sources it used.

There should be no hallucinations since it's basing responses directly on the provided data sources in realtime and not guessing based on some vague trained data that we know nothing about.

The script does need to be continuously running in order to use it, so if you turn off the script/computer, it will not work. In order to keep it running always, you can either buy a mini computer that is all the time or rent it through a cloud service like Railway.com.

## Features

- `/vocab` — searches Arabic vocabulary dictionaries on tafsir.app first, then falls back to Turath lugha categories.
- `/verse` — retrieves tafsir for a specific Qur'an verse from tafsir.app and Quran.com tafsir pages.
- `/tafsir` — searches preferred Turath tafsir books first, then falls back to the general Turath tafsir category.
- Plain text routing — users can ask without commands, and the bot will try to route the request automatically.
- Specific mufassir targeting — if the user names a supported mufassir, the bot searches that mufassir's mapped Turath book ID instead of all preferred tafsir books.
- Private or public mode — restrict usage to one Telegram user ID or allow anyone to use the bot.

## Commands

```text
/start
Show the intro message and examples.

/help
Show command help.

/id
Return your Telegram user ID. Use this when setting up a private bot.

/vocab [word or question]
Examples:
/vocab يوم
/vocab What does يوم mean?
/vocab ما معنى يوم؟

/verse [surah:ayah]
Examples:
/verse 1:4
/verse 2:255

/tafsir [question]
Examples:
/tafsir What did Qurtubi say about worship?
/tafsir تفسير قوله تعالى إياك نعبد وإياك نستعين
```

Users may also send plain messages without commands. For example:

```text
What does يوم mean?
What did Ibn Kathir say about sincerity?
Give tafsir for 1:4
ما معنى يوم؟
```

## Source layers

### Vocabulary

The `/vocab` command searches tafsir.app dictionaries first:

```python
ARABIC_VOCAB_SOURCES = [
    "mufradat-ragheb",
    "lisan",
    "qamoos",
    "maqayees",
]
```

If no tafsir.app dictionary result is found, it falls back to Turath lugha categories:

```python
TURATH_CATEGORY_ARABIC_VOCAB_1 = 29
TURATH_CATEGORY_ARABIC_VOCAB_2 = 30
```

### Specific verse tafsir

The `/verse` command uses tafsir.app sources plus configured Quran.com tafsir pages.

Edit these sections to add or remove sources:

```python
TAFSIR_APP_SOURCES = [...]
TAFSIR_APP_SOURCE_LABELS = {...}
QURAN_COM_TAFSIR_SOURCES = [...]
```

### General tafsir search

The `/tafsir` command searches the preferred Turath tafsir books first:

```python
PREFERRED_TAFSIR_BOOK_IDS = [
    43,     # Tabari
    1503,   # Ibn Kathir
    23626,  # Ibn Juzayy
    20855,  # Qurtubi
    9776,   # Ibn Ashur
    18686,  # Tha'labi
    8346,   # Al-Mawardi
    13231,  # Al-Wahidi's Al-Baseet
    21821,  # Al-Wahidi's Al-Wasit
    41,     # Al-Baghawi
    1394,   # Al-Nasafi
    23627,  # Al-Zamakhshari
    23632,  # Ibn Atiyyah
    23619,  # Ibn al-Jawzi
    23635,  # Al-Razi
    23588,  # Al-Baydawi
]
```

If the preferred books do not provide enough results, the bot falls back to Turath tafsir category:

```python
TURATH_CATEGORY_TAFSIR = 3
```

## Specific mufassir targeting

The bot can detect common mufassir names and search only the matching book IDs.

For example:

```text
What did Qurtubi say about worship?
```

This searches only Qurtubi's mapped Turath book ID:

```python
{"label": "Al-Qurtubi", "book_ids": [20855], "aliases": ["qurtubi", "al-qurtubi", "القرطبي"]}
```

To add another mufassir, add a new entry to:

```python
PREFERRED_TAFSIR_AUTHOR_BOOKS = [...]
```

Use this pattern:

```python
{
    "label": "Author Display Name",
    "book_ids": [12345],
    "aliases": ["english alias", "another spelling", "Arabic name"],
}
```

If an author has more than one Turath book ID, include all of them:

```python
{
    "label": "Al-Wahidi",
    "book_ids": [13231, 21821],
    "aliases": ["wahidi", "al-wahidi", "الواحدي"],
}
```

## Context expansion settings

Turath search results often return a target page. To capture context before and after the target page, the bot fetches neighboring pages.

Current settings:

```python
TURATH_CONTEXT_TOP_N = 5
TURATH_CONTEXT_RADIUS = 3
```

Meaning:

- Expand the top 5 Turath results.
- For each expanded result, fetch 3 pages before and 3 pages after the target page.
- Total per expanded result: up to 7 pages.

To expand more results:

```python
TURATH_CONTEXT_TOP_N = 8
```

To increase surrounding pages:

```python
TURATH_CONTEXT_RADIUS = 5
```

This would fetch 5 pages before, the target page, and 5 pages after.

Be careful with very high settings. More context can improve answers, but it also makes the bot slower and can send too much text to the OpenAI model.

Practical settings:

```python
# Balanced
TURATH_CONTEXT_TOP_N = 5
TURATH_CONTEXT_RADIUS = 3

# Deeper research
TURATH_CONTEXT_TOP_N = 8
TURATH_CONTEXT_RADIUS = 5

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/tafsir-vocab-telegram-bot.git
cd tafsir-vocab-telegram-bot
```

### 2. Create a virtual environment

## Option 1: Simple install

If you do not want to use a virtual environment, install the packages directly:

```bash
pip install -r requirements.txt
python bot.py
```

## Option 2: Virtual environment install

To use it in a virtual environment, install the packages as:

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create your `.env` file

Copy the example file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_MODEL=gpt-5.4-mini
PUBLIC_BOT=false
ALLOWED_TELEGRAM_USER_ID=123456789
```

### 5. Run the bot

```bash
python tafsir.py
```

You should see:

```text
Tafsir & Vocabulary Telegram bot is running...
```

## Setting up your Telegram bot

Telegram bots are created and managed through `@BotFather`.

### Create a bot

1. Open Telegram.
2. Search for `@BotFather`.
3. Send:

```text
/newbot
```

4. Choose a display name.
5. Choose a username. Telegram bot usernames must end in `bot`, for example:

```text
my_tafsir_bot
```

6. BotFather will give you a bot token.
7. Paste that token into your `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_token_here
```

Keep this token secret. Anyone with the token can control your bot.

### Set the command menu

In `@BotFather`, send:

```text
/setcommands
```

Choose your bot and paste:

```text
vocab - Search Arabic vocabulary dictionaries and lugha sources
verse - Search tafsir for a specific verse
tafsir - Search preferred tafsir books and Turath tafsir category
help - Show usage help
id - Show your Telegram user ID
```

Telegram command names should be lowercase, simple, and without the slash when entered into BotFather's command list.

## Public vs private mode

This bot supports two access modes.

### Private mode

Private mode is best while testing or if the bot is only for you.

In `.env`:

```env
PUBLIC_BOT=false
ALLOWED_TELEGRAM_USER_ID=123456789
```

To get your Telegram user ID:

1. Temporarily run the bot.
2. Message your bot:

```text
/id
```

3. Copy the ID returned by the bot.
4. Paste it into `.env` as `ALLOWED_TELEGRAM_USER_ID`.
5. Restart the bot.

When private mode is enabled, only that Telegram user ID can use the bot. Other users will see:

```text
This bot is private.
```

### Public mode

Public mode allows anyone who can find or message the bot to use it.

In `.env`:

```env
PUBLIC_BOT=true
```

When public mode is enabled:

- You do not need `ALLOWED_TELEGRAM_USER_ID`.
- Anyone can use your OpenAI usage through the bot.
- You should monitor costs and logs.
- You may want rate limiting before heavily promoting it.

## Telegram privacy mode for groups

Telegram has its own BotFather privacy setting for group chats. This is separate from the `PUBLIC_BOT` setting in this code.

- `PUBLIC_BOT=false` means the Python code rejects everyone except your allowed Telegram user ID.
- Telegram's group privacy mode controls what messages the bot can see when added to groups.

For a public bot in private chats, you usually do not need to change Telegram group privacy mode. If you add the bot to groups and want it to read non-command messages, review BotFather's privacy mode settings carefully.

## How the bot decides which source layer to use

Plain messages are routed roughly as follows:

1. If the message looks like a vocabulary question, use the vocabulary source layer.
2. If it contains a verse reference like `1:4`, use the specific verse tafsir source layer.
3. Otherwise, use the general tafsir source layer.
4. If a supported mufassir name is detected, search that mufassir's mapped Turath book ID first.

You can adjust routing behavior in:

```python
plain_message(...)
is_vocab_like(...)
is_verse_like(...)
detect_tafsir_author_request(...)
```

## Adding or changing sources

### Add a tafsir.app verse source

Add the source ID to:

```python
TAFSIR_APP_SOURCES = [...]
```

Then add a display label:

```python
TAFSIR_APP_SOURCE_LABELS = {
    "source-id": "Readable Name",
}
```

### Add a Quran.com tafsir source

Add an object to:

```python
QURAN_COM_TAFSIR_SOURCES = [
    {
        "source_id": "source-id",
        "source_name": "Readable Name",
        "author": "Author Name",
        "language": "arabic",
        "url_template": "https://quran.com/{surah}:{ayah}/tafsirs/source-id",
    },
]
```

### Add a preferred Turath tafsir book

Add the Turath book ID to:

```python
PREFERRED_TAFSIR_BOOK_IDS = [...]
```

Optionally add author targeting in:

```python
PREFERRED_TAFSIR_AUTHOR_BOOKS = [...]
```

### Add a vocabulary dictionary on tafsir.app

Add the source ID:

```python
ARABIC_VOCAB_SOURCES = [...]
```

Add the readable label:

```python
ARABIC_VOCAB_SOURCE_LABELS = {
    "source-id": "Readable Dictionary Name",
}
```

### Add or change Turath fallback categories

Vocabulary fallback categories:

```python
TURATH_LUGHA_CATEGORIES = [29, 30]
```

General tafsir fallback category:

```python
TURATH_CATEGORY_TAFSIR = 3
```

## Security notes

- Never commit `.env` to GitHub.
- Never share your Telegram bot token.
- Never share your OpenAI API key.
- Rotate the Telegram token through BotFather if it is exposed.
- Keep `PUBLIC_BOT=false` until you are ready for public usage.
- Public bots can create real API costs.

## Troubleshooting

### The bot says `Missing TELEGRAM_BOT_TOKEN`

Make sure your `.env` file exists and contains:

```env
TELEGRAM_BOT_TOKEN=...
```

### The bot says `Missing OPENAI_API_KEY`

Make sure your `.env` file contains:

```env
OPENAI_API_KEY=...
```

### The bot says `This bot is private`

You are running with:

```env
PUBLIC_BOT=false
```

Set your actual Telegram user ID:

```env
ALLOWED_TELEGRAM_USER_ID=your_id_here
```

or switch to public mode:

```env
PUBLIC_BOT=true
```

### The bot runs but does not respond

Check:

- You are messaging the correct Telegram bot.
- The token in `.env` belongs to that bot.
- Your Python process is still running.
- There are no errors in the terminal.
- If private mode is enabled, your Telegram user ID is correct.

## Recommended repository structure

```text
tafsir-vocab-telegram-bot/
├── tafsir.py
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Disclaimer

This bot is a research assistant. It retrieves excerpts from configured sources and asks the model to answer only from those excerpts. It should not be treated as an independent authority.
