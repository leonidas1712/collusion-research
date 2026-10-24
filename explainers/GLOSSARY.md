# Glossary

- **First-action round:** the round in which the target first does the forbidden thing (e.g. posts the token).
- **Residual stream:** the list of numbers each token carries through the model; every layer reads it and adds to it. 5,120 numbers in Qwen3-32B.
- **Linear probe:** weights w and bias b; score = sigmoid(w·h + b) on one residual-stream vector h.
- **AUROC:** chance a random positive scores above a random negative. 0.5 is guessing, 1.0 is perfect.
- **Monitor ladder:** LLM-judge monitors that see progressively more: actions only, then the conversation, then unposted text, then reasoning.
- **Lead time:** how many turns before the action a detector first raises an alarm.
