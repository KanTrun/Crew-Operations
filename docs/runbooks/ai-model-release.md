# AI Model and Rule Release

1. Record the agent, prompt, model, rule version, rollout bucket, and policy action with every generation.
2. Run deterministic quality and policy checks before any send action.
3. Reflection may create pending proposals from evidence; it cannot activate a model behavior or rule.
4. A `chu_quan` reviews evidence, resolves deterministic conflicts, approves, and then activates a rule.
5. Monitor evaluation summary and feedback after activation. Pause or roll back immediately when quality or safety regresses.

Use the circuit breaker before emergency investigation. It is owner-controlled and forces Gmail to stop before transport and Facebook Messenger to review queue behavior.