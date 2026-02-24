# Update .env for Model Broker

To switch to the HPE in-house Model Broker, update your `.env` file with these settings:

## Required Changes

1. **Change the AI provider:**
   ```env
   AI_PROVIDER=modelbroker
   ```

2. **Add your Model Broker Virtual Key:**
   ```env
   MODELBROKER_API_KEY=your-virtual-key-here
   ```

3. **Set the model (optional, defaults to llama-3.3-70b):**
   ```env
   MODELBROKER_MODEL=llama-3.3-70b
   ```

4. **Set the base URL (optional, uses default if not set):**
   ```env
   MODELBROKER_BASE_URL=https://model-broker.aviator-model.bp.anthos.otxlab.net
   ```

## Complete Example

Add these lines to your `.env` file:

```env
# AI Configuration - HPE Model Broker (In-house LLM)
AI_PROVIDER=modelbroker
MODELBROKER_API_KEY=your-virtual-key-here
MODELBROKER_MODEL=llama-3.3-70b
MODELBROKER_BASE_URL=https://model-broker.aviator-model.bp.anthos.otxlab.net
```

## After Updating

1. Restart the backend container:
   ```bash
   docker restart logwatch-backend
   ```

2. Verify the change in the logs:
   ```bash
   docker logs logwatch-backend | grep "Model Broker"
   ```
   
   You should see: `Initialized Model Broker provider: https://model-broker.aviator-model.bp.anthos.otxlab.net with model: llama-3.3-70b`

## Switching Back to Groq (Optional)

If you need to switch back to Groq, just change:
```env
AI_PROVIDER=groq
GROQ_API_KEY=your-groq-key
```

## Available Models

Check your Model Broker dashboard for available models. Common options:
- `llama-3.3-70b` (default)
- `llama3`
- `gemma`
- And others listed in your dashboard

---

**Note:** Your Model Broker Virtual Key is sensitive. Keep it secure and don't commit it to version control.
