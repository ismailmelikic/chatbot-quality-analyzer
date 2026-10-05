# Chatbot Quality Analyzer

Upload your chatbot's conversation logs and get a quality report: the tool
**discovers conversation topics on its own**, **detects failed conversations**,
**tracks trends over time** and can turn the findings into a **plain-language
management report**.

It runs entirely on your own computer. Nothing is collected, there is no
account and no telemetry — see [Your data](#-your-data).

The interface is available in English and Turkish; failure detection
understands English and Turkish bot replies.

---

## 🚀 Getting started

**Requirement:** [Python 3.11 or newer](https://www.python.org/downloads/).

Download the project (green **Code** button → *Download ZIP*, or `git clone`),
then:

| System | How to start |
|---|---|
| **macOS** | Double-click **`start.command`** in Finder. If macOS blocks it: right-click → **Open** → **Open** (only the first time). |
| **Windows** | Double-click **`start.bat`**. When installing Python, tick *"Add python.exe to PATH"*. |
| **Linux** | Run `bash start.command` in a terminal. |

The **first start** creates a virtual environment and installs the
dependencies — this takes a few minutes and happens once. The panel then opens
in your browser at `http://localhost:8501`. Stop it with `Ctrl+C` in the
terminal window.

The first analysis also downloads the embedding model
([`paraphrase-multilingual-MiniLM-L12-v2`](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2),
~470 MB) once. After that, analysis works offline.

<details>
<summary>Manual setup (any system)</summary>

```bash
python3 -m venv .venv
```

```bash
./.venv/bin/pip install -r requirements.txt
```

```bash
./.venv/bin/streamlit run dashboard.py
```

On Windows use `.venv\Scripts\pip` and `.venv\Scripts\streamlit` instead.
</details>

---

## 📤 Analyzing your logs

In the sidebar: **Upload your logs** → choose a file → **Run analysis**.
A log of ~600 conversations takes about 40 seconds.

**You don't need to edit your file.** The tool recognizes common formats on its
own.

Want to try it first? Upload **`ornek_musteri_loglari.csv`** from the project
folder — a synthetic Turkish telecom support log (620 conversations).

### Supported formats

**File types:** CSV, JSON, JSONL.

**Two layouts are accepted:**

1. *One row = one question/answer pair* — the user message and the bot reply
   in the same row.
2. *One row = one message + a role column* — the layout written by Rasa,
   Dialogflow, LangChain, OpenAI and similar platforms. Messages are ordered
   per conversation and paired automatically; consecutive messages from the
   same side are merged.

**Recognized column names:**

| Meaning | Recognized names |
|---|---|
| User message | `user_message`, `query`, `question`, `prompt`, `input`, `instruction`, `kullanici_mesaji`… |
| Bot reply | `response`, `answer`, `reply`, `bot_response`, `output`, `completion`, `chatbot_cevabi`… |
| Conversation | `conversation_id`, `session_id`, `dialog_id`, `chat_id`, `thread_id`, `oturum_id`… |
| Turn | `turn`, `turn_index`, `sequence`, `message_index`, `sira_no`… |
| Date | `date`, `timestamp`, `created_at`, `datetime`, `tarih`… |
| Role *(layout 2)* | `role`, `sender`, `speaker`, `author`, `is_bot`, `inbound`… — values like `user`/`bot`, `customer`/`agent`, `true`/`false` |

If a column still isn't recognized, the panel asks you which column is which —
still no file editing. Full list: `KOLON_IPUCLARI` in `pipeline.py`.

### Optional columns

| Column | If missing |
|---|---|
| Conversation ID | Every row is treated as a separate conversation |
| Turn | Rows keep their file order within a conversation |
| Date | The *Time Trends* tab is hidden |

If your data happens to contain labels, the tool also measures its own
accuracy against them: `gercek_konu` (true topic → clustering ARI/NMI),
`sonuc_durumu` (true outcome → rule accuracy), `belirsiz_mesaj` (whether the
user message was ambiguous: `yes`/`no`). Real logs normally don't have these;
the tool works fully without them.

---

## 🔍 How it works

```
log → format detection → embeddings + KMeans → rule-based failure detection → trends → LLM report (optional)
```

**Topic discovery — no labels used.** The first message of every conversation
is turned into a multilingual sentence embedding and clustered with KMeans.
The number of clusters is chosen by silhouette score, not by hand.

**Failure detection — from the bot's reply text.** Real logs rarely say
whether a conversation failed, so `kurallar.py` infers it:

- **Fallback** — *"I don't understand"*, *"could you rephrase"*,
  *"I can't help with that"* / *"anlayamadım"*, *"tekrar ifade eder misiniz"*
- **Hand-over to a human** — a hand-over verb (*transfer you*, *connect you*)
  **and** a human target (*human agent*, *customer service*) in the same
  reply. A verb alone isn't enough: *"I'm redirecting you to our offers"* is
  not a failure.
- **Repeated question** — a fallback reply after the first turn

A conversation counts as failed if any of its turns does.

**If the rules don't fit your logs.** The patterns are language-specific.
When a sizeable log matches none of them, the panel says so explicitly instead
of reporting a reassuring but false "0% failure". To adapt the tool to your
bot, edit the pattern lists in `kurallar.py` (`FALLBACK_KALIPLARI`,
`INSAN_HEDEFI_KALIPLARI`, `DEVIR_FIILI_KALIPLARI`).

> Patterns are not literal translations. Turkish *"daha detay verebilir
> misiniz"* signals the bot giving up, but English *"could you provide more
> details"* is a routine clarifying question — it was measured to inflate the
> failure rate from 1.8% to 7.2%, so it is deliberately left out.

### Panel tabs

| Tab | Content |
|---|---|
| Topic Clusters | 2-D map of the discovered clusters and their sizes |
| Failure Analysis | Failure rate per cluster, how failed conversations ended |
| Time Trends | Weekly volume and failure rate, volume spikes, monthly changes — *only if the log has dates* |
| Executive Report | Report written by an LLM from the numbers *(optional)* |

---

## 🔒 Your data

- **Everything runs on your machine.** The panel only listens on `localhost`,
  so other devices on your network can't open it. Usage statistics are
  disabled. Results are written to the `yuklenen_analiz/` folder inside the
  project.
- **The LLM features are optional** (naming clusters, writing the report).
  Clustering, failure detection and trends work without them.
- **If you use an LLM,** data goes only to the provider *you* choose, with
  *your* key:
  - *Naming clusters* sends up to 10 example user messages per cluster.
  - *The report* sends only aggregate numbers and cluster names — no messages.
- **Fully offline option:** install [Ollama](https://ollama.com), pull a model
  (`ollama pull llama3.1`) and choose *Local / Custom (Ollama, vLLM, on-prem)*
  in the LLM settings. The pre-filled address `http://localhost:11434/v1` is
  Ollama's default on every machine, and no API key is needed. Then no data
  leaves your computer.
- **API keys are never written to disk.** They live in the browser session or
  come from an environment variable. Only the provider and model choice are
  saved to `ayarlar.json`.

---

## 🔑 LLM settings

Sidebar → **LLM settings → Provider and model**. Supported: Hugging Face,
NVIDIA NIM, OpenAI and any OpenAI-compatible local server (Ollama, vLLM).
**Test** checks the connection.

Instead of typing the key in the panel, you can set an environment variable
before starting: `HF_TOKEN`, `NVIDIA_API_KEY`, `OPENAI_API_KEY` or
`LLM_API_KEY` (local), depending on the provider.

Free model catalogs change often, so no model name is hard-coded.
**Auto-find a working model** tries the candidates one by one and saves the first
one that actually answers.

> ⚠️ **Avoid "reasoning" models** (GLM, MiMo, Nemotron-3, gpt-oss, `*-R1`,
> QwQ). Their thinking phase uses up the token budget: they pass the short
> connection test but return an empty report. Use plain *instruct* models —
> tested: `meta-llama/Llama-3.3-70B-Instruct`, `Qwen/Qwen2.5-72B-Instruct`.

---

## 📊 Results on the sample data

The sample data (`telekom_chatbot_loglari.csv`, synthetic, 620 conversations)
includes true topic labels, so clustering quality can be measured:

| Method | ARI | NMI |
|---|---|---|
| TF-IDF, words (1–2 grams) | 0.02 | 0.19 |
| TF-IDF, characters (3–5 grams) | 0.19 | 0.37 |
| **Embeddings + KMeans** | **0.451** | **0.559** |

TF-IDF couldn't separate topics in Turkish, hence semantic embeddings.
(The TF-IDF rows were measured during development; that comparison script is
not part of the repository.) Upload `telekom_chatbot_loglari.csv` to reproduce
the embedding result in the panel.

Overall failure rate: **29.0%**. The rules reproduce the synthetic outcome
labels **100%** — expected, since the data was generated from fixed templates;
real logs will score lower.

---

## 📁 Project structure

| File | Purpose |
|---|---|
| `dashboard.py` | Streamlit panel |
| `pipeline.py` | Format detection and the full analysis → `yuklenen_analiz/` |
| `kurallar.py` | Rule-based failure detection (English + Turkish) |
| `llm.py` | LLM settings, report writing, cluster naming |
| `diller.py` | Interface texts (English + Turkish) |
| `start.command` / `start.bat` | Launchers (macOS/Linux, Windows) |
| `ornek_musteri_loglari.csv` | Sample log without labels — try the tool with it |
| `telekom_chatbot_loglari.csv` | Same data with labels — for measuring accuracy |

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| macOS: double-click does nothing | In Terminal: `chmod +x start.command` |
| macOS: "cannot be opened" warning | Right-click the file → **Open** → **Open** |
| "Python 3.11 or newer is required" | Install Python from python.org and start again |
| Setup failed halfway | Delete the `.venv` folder and start again |
| Report or cluster names are empty | Enter an API key in the LLM settings, then press the button |
| Port 8501 is busy | The launcher picks the next free port; use the address it prints |

---

## 📄 License

[MIT](LICENSE) — free to use, modify and share; keep the license notice.
