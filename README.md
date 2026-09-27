---
title: ShopAssist
sdk: docker
app_port: 7860
---

# ShopAssist: Voice-Enabled Shopping Support

A runnable academic project with a trained PyTorch BiLSTM, 27 shopping-support intents, browser speech recognition, optional spoken replies and stateful order-support flows. **All orders, refunds and store policies are fictional.** No paid AI API key is needed.

## Run it locally

Use **Python 3.12**. The trained model is already included; do not retrain just to run the app.

macOS / Linux:

```sh
cd shopassist
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows PowerShell:

```powershell
cd shopassist
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Open **http://localhost:7860** in Chrome. Allow microphone access, speak, review the transcript and send it. Typed chat also works. Installation downloads PyTorch and can take a few minutes. No GPU is required. The Windows launcher uses Python 3.12; the shell launcher uses whichever `python3` is installed, so confirm its version first.

## Five sample orders

| Order | Starting state | Try |
|---|---|---|
| 1041 | Processing | Cancel, decline/confirm, or change its fictional address |
| 1042 | Shipped | Track delivery or download demo receipt; cancellation is blocked |
| 1043 | Delivered 3 days ago | Request a return, give a reason, confirm |
| 1044 | Returned | Check an already-processing refund |
| 1045 | Delivered 40 days ago | Check the expired return window |

Dates are generated relative to the session's creation date. Each browser session gets separate orders. Reset demo requires a second click and restores only that session. Changes are persisted in SQLite within the running instance but may reset when a free host restarts.

## Model and dataset

- Bitext Customer Support v11: 26,872 rows, 27 intents. The original is synthetic/hybrid data, not real-user transcripts.
- Normalized deduplication leaves 23,619 rows, split 70/15/15 with seed 42.
- A separately marked authored training supplement improves short, natural shopping questions. Its normalized overlaps with validation/test data are excluded.
- Model: word embedding (64) → bidirectional LSTM (64 units per direction) → dropout → Dense(64, ReLU) → dropout → Dense(27).
- AdamW training, cross-entropy, gradient clipping and best validation macro-F1 checkpoint. A validation-selected threshold and fixed margin/vocabulary coverage checks request clarification for uncertain inputs.
- A state machine uses the detected intent plus order IDs and follow-up answers. It requires confirmation before cancelling, changing an address or recording a return. These control replies are deterministic; they are not represented as separate trained intents.

**Read reports/metrics.json and reports/challenge_results.json together.** The synthetic held-out score is high, but the smaller, differently phrased challenge shows substantially weaker generalization. Do not present synthetic test accuracy as real-user or speech accuracy. Unknown requests can still be misclassified confidently.

## Reproduce training and evaluation

```sh
python -m pip install -r requirements-train.txt
python data/augment.py
python train.py
python evaluate_challenge.py
python -m unittest discover -s tests -v
```

Training runs on CPU. Splits, vocabulary, weights, logs, predictions and metrics are included. `download_dataset.py` is optional; use the included dataset snapshot for exact input reproduction. The vocabulary is fit only to the training data. The inference model is loaded with `weights_only=True`.

## Deploy on Render

1. Create a GitHub repository and upload the **contents** of this folder so Dockerfile is at the repository root. Include models/intent_bilstm.pt and models/metadata.json.
2. In Render, create a **Web Service** from that repository. Choose **Docker**, then **Free** if available for your account.
3. Use the provided Dockerfile and leave the Docker command override blank. Set the health-check path to `/health`.
4. Add `SECRET_KEY` as a randomly generated secret and `COOKIE_SECURE=1`. Do not commit the secret. `DATABASE_PATH=/tmp/shopassist.sqlite3` is the default.
5. Deploy, wait for Live, then test the public HTTPS URL on a device with a microphone.

Alternatively, import the repository as a Render Blueprint using render.yaml; it generates SECRET_KEY and sets the other configuration. The service uses one Gunicorn worker and four threads to keep memory use moderate and ensure consistent session secrets. The Docker image is configured to respect Render's PORT variable.

Render's free service may sleep after inactivity and lose local SQLite data when restarted. This is acceptable for disposable demo orders. Open the link before an evaluation and allow time for a cold start. No live URL is claimed until a deployment has actually succeeded.

Official references: https://render.com/docs/docker and https://render.com/docs/free

## Alternative: Hugging Face Docker Space

Create a public Docker Space and upload the application source plus model artifacts, Dockerfile and this README. The YAML header selects Docker and port 7860. The API serves the frontend itself. Use the direct app URL for microphone testing; embedded iframe permissions may differ. This route still needs a hosting account and an actual successful deployment.

## Project layout

- `app.py`, `wsgi.py`: Flask endpoints, per-session state, idempotent message handling and production entry point.
- `engine.py`: order lookup, confirmation and multi-turn support policy.
- `model.py`, `models/`: tokenization, BiLSTM and learned parameters.
- `static/`: responsive interface, microphone transcript, chat and speech synthesis.
- `data/`: attributed dataset projection, split records and authored supplement.
- `train.py`, `evaluate_challenge.py`: reproducible experiments.
- `tests/test_app.py`: functional checks using the actual trained classifier.
- `reports/`: metrics, training history, per-example predictions, test output and report.
- `Dockerfile`, `render.yaml`: external hosting configuration.

## Privacy and scope

Use fictional details only. This is a public demonstration without customer authentication. Each signed session stores sample orders and up to 100 recent message requests/results for idempotent retries. Records expire after 24 hours of inactivity and are cleaned during subsequent requests. Reset clears the session's message records. Hosting logs may contain normal request metadata. Audio is handled by the browser's recognition provider, not uploaded to this Flask server. SpeechRecognition support varies; typed input is always available.

This is not a generative LLM. Responses are controlled templates populated with demo data. Account registration, real checkout, human-agent transfer, newsletters and real payment processing are intentionally not connected; the app says so when those intents are detected. Return pickup and refund processing are simulated statuses.

## Submission

Submit the externally deployed URL, the source ZIP or repository, and reports/ShopAssist_Report.pdf. Complete reports/MANUAL_TESTS.md on your actual browser before claiming measured speech accuracy or end-to-end latency.

## Licensing

Original application code: MIT (LICENSE). Bitext-derived data: the separate license in data/LICENSE.txt; see data/SOURCE.md for attribution and modifications. Preserve both when redistributing.
