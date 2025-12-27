# Railway Deployment Guide

## ✅ What's Configured

Your project is ready for Railway deployment with:
- `Procfile` - Railway start command
- `railway.json` - Railway configuration
- `requirements.txt` - Updated with gunicorn
- `src/app.py` - Flask app with automatic environment detection

## 🚀 Deploy to Railway

### Step 1: Configure in Railway Dashboard

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect the Python app

### Step 2: Set Environment Variables

In Railway Dashboard → Variables tab, add:

```
REDUCTO_API_KEY=953c875e9dee4077b916bbfda9fcd6893c781fa9b433df585fa2e1dc124ad23412a759b70ce1c6b338985b5fc8a8485f
OPENAI_API_KEY=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
SUPABASE_URL=https://bxikvimqolpglfuampcl.supabase.co
SUPABASE_KEY=sb_secret_HmdIMrTnudA-IgIQqxiq6w_7LFghy6B
FLASK_SECRET_KEY=your_production_secret_key_here
```

⚠️ Generate a new `FLASK_SECRET_KEY` for production:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 3: Configure Start Command (Optional)

Railway should auto-detect from `Procfile`, but if needed, set:

**Start Command:**
```
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 src.app:app
```

**Or simpler (from railway.json):**
Railway will use the configuration from `railway.json` automatically.

### Step 4: Deploy

Click "Deploy" - Railway will:
1. Install dependencies from `requirements.txt`
2. Run the start command from `Procfile`
3. Expose your app on a public URL

## 📝 Configuration Files

### `Procfile`
```
web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 src.app:app
```

### `railway.json`
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 src.app:app"
  }
}
```

## 🔧 Command Breakdown

```bash
gunicorn \
  --bind 0.0.0.0:$PORT    # Bind to Railway's assigned port
  --workers 2              # 2 worker processes
  --timeout 120            # 120 second timeout for long requests
  src.app:app              # Import path: src/app.py → app variable
```

## 📊 Important Notes

### File Storage
- Railway provides **persistent storage** (unlike Vercel)
- Files in `/tmp` are preserved between requests
- All files also backed up to Supabase Storage

### Environment Detection
The app automatically detects Railway via environment variables and uses:
- `/tmp/uploads` and `/tmp/export` for temporary files
- Supabase for permanent storage

### Workers & Performance
- **2 workers** configured (good for small apps)
- Increase workers for higher traffic: `--workers 4`
- Each worker can handle multiple concurrent requests

### Timeout
- **120 seconds** configured (generous for document processing)
- Reducto API calls can take 20-40 seconds
- Adjust if needed: `--timeout 180`

## 🐛 Troubleshooting

### "Application failed to start"
1. Check Railway logs for the error
2. Verify all environment variables are set
3. Make sure `requirements.txt` has all dependencies

### "ModuleNotFoundError"
1. Check that imports use relative imports (from .module)
2. Verify the start command path: `src.app:app`
3. Check Railway build logs

### "Connection to Supabase failed"
1. Verify SUPABASE_URL and SUPABASE_KEY are correct
2. Check Supabase project is active
3. Verify network access from Railway

### Logs showing port errors
Railway sets `$PORT` automatically - don't hardcode port numbers

## 📈 Monitoring

### View Logs
Railway Dashboard → Your Service → Logs

### Metrics
Railway Dashboard → Your Service → Metrics
- CPU usage
- Memory usage
- Request count

## 🔄 Continuous Deployment

Once connected to GitHub:
- Push to `main` → Auto-deploy to production
- Railway rebuilds and redeploys automatically

## 💰 Pricing

Railway offers:
- **Free tier**: $5 credit/month
- **Developer plan**: $5/month + usage
- **Team plan**: $20/month + usage

Document processing may use credits due to:
- Long-running requests (Reducto API)
- File storage
- Outbound bandwidth

## ⚡ Performance Tips

1. **Enable Caching**: Add Redis for session storage
2. **Optimize Workers**: Monitor and adjust based on traffic
3. **Database Connection Pooling**: Already handled by Supabase client
4. **Static Files**: Serve from CDN for production

## 🎉 Success!

If deployment succeeds, you'll see:
```
✓ Build successful
✓ Deployment live
Your app is available at: https://your-app.railway.app
```

Test these endpoints:
- `https://your-app.railway.app/` - Homepage
- `https://your-app.railway.app/customers` - Customers
- `https://your-app.railway.app/po/upload` - Upload PO
