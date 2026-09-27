# Browser and speech acceptance checks

Automated Flask API/state tests: 17 passed. JavaScript syntax: passed.
Browser UI and microphone tests: NOT COMPLETED. The available browser preview could not run the Python server in its separate runtime. These require the deployed HTTPS app or localhost on the evaluator's device.

| Test | Expected | Actual |
|---|---|---|
| Desktop and phone | Orders, conversation and composer visible without horizontal page overflow | To measure |
| Speak "Track order 1042" | Transcript visible; user can edit and send; shipped response | To measure |
| Speak order digits separately | Numeric ID or recognized digit words accepted | To measure |
| Deny microphone permission | Helpful error; typed chat works | To measure |
| Stop listening / silence | Recording ends; no unintended submission | To measure |
| Speech-unavailable browser | Type-input fallback is usable | To measure |
| Read replies aloud | Reply speaks; disabling toggle cancels speech | To measure |
| Cancel order 1041 then No | Order stays processing | To measure |
| Cancel order 1041 then Confirm | Cancelled with demo refund processing | To measure |
| Return order 1043 -> Wrong size -> Confirm | Return requested; refund awaits item approval | To measure |
| Return order 1045 | Expired return-window explanation | To measure |
| Refresh / another browser session | State retained in same session; independent elsewhere | To measure |
| Keyboard-only controls / 200% zoom | All core controls remain usable | To measure |

For speech accuracy, read at least 20 unused questions, record the reference and the unedited transcript, and calculate WER=(substitutions+deletions+insertions)/reference words. Report speaker count, browser, microphone, noise, intent accuracy from transcripts and end-to-end response latency. Model CPU inference time is not end-to-end speech latency.
