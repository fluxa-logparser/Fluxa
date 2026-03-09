# OpenAI API Key Setup Guide

This guide explains how to set up your OpenAI API key for using DeepParse functionality.

## Step 1: Get Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to [API Keys page](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy the generated key (format: `sk-proj-...`)

**Important**: Keep your API key secure and never commit it to GitHub!

## Step 2: Set Your API Key

### Option 1: Environment Variable (Recommended)

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-proj-your-actual-key-here"
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-proj-your-actual-key-here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-proj-your-actual-key-here"
```

To make it permanent, add to your shell profile:
- **Linux/Mac**: Add to `~/.bashrc` or `~/.zshrc`
- **Windows**: Add to Environment Variables in System Settings

### Option 2: Command Line Argument

```bash
python logparser/DeepParse/demo.py -key sk-proj-your-actual-key-here --dataset HDFS
```

### Option 3: In Python Code

```python
import openai
openai.api_key = "sk-proj-your-actual-key-here"
```

## Step 3: Verify Your API Key

Test your API key:

```bash
cd logparser/DeepParse
python demo.py -key sk-proj-your-key --dataset HDFS --limit 10
```

If successful, you should see parsing results. If you get authentication errors, check:
- API key is correct (no extra spaces)
- API key has active credits
- Internet connection is working

## API Key Security Best Practices

### ✅ DO:
- Keep API keys in environment variables
- Use `.env` files (add to `.gitignore`)
- Rotate keys periodically
- Monitor usage in OpenAI dashboard

### ❌ DON'T:
- Commit API keys to Git
- Share API keys publicly
- Hardcode keys in source code (we removed this!)
- Print keys in logs or output

## Troubleshooting

### Error: "The API key provided is not valid"
**Solution**: Check for typos, ensure key starts with `sk-proj-`

### Error: "You exceeded your current quota"
**Solution**: Add credits to your OpenAI account at https://platform.openai.com/account/billing

### Error: "Rate limit exceeded"
**Solution**: Wait a few minutes and try again, or upgrade your plan

## Cost Estimation

DeepParse uses OpenAI's embedding API for log similarity:

- **Embedding generation**: ~$0.0001 per 1K tokens
- **GPT-3.5-turbo-instruct**: ~$0.002 per 1K tokens
- **Estimated cost for 2K logs**: ~$0.50-2.00 depending on model

For the full 16-dataset benchmark (~32K logs):
- Embeddings (one-time): ~$3-5
- Parsing: ~$10-30

**Tip**: Use BulkParse for known patterns to reduce API costs!

## Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OpenAI Pricing](https://platform.openai.com/pricing)
- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)

---

**Need Help?** Open an issue on GitHub or contact the maintainers.
