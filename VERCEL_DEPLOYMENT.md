# Vercel Deployment Guide

## Files Created for Vercel

1. **`vercel.json`** - Vercel configuration file
2. **`api/index.py`** - Serverless function entry point
3. **`.vercelignore`** - Files to exclude from deployment

## Important Notes

### Database Configuration

⚠️ **SQLite on Vercel has limitations:**
- SQLite database is stored in `/tmp` directory (ephemeral)
- Data will be lost on each deployment
- **Recommended:** Use PostgreSQL with Vercel Postgres addon

### To Use PostgreSQL on Vercel:

1. Go to your Vercel project dashboard
2. Navigate to Storage → Create Database → Postgres
3. Copy the `DATABASE_URL` connection string
4. Add it as an environment variable in Vercel:
   - Go to Settings → Environment Variables
   - Add `DATABASE_URL` with your PostgreSQL connection string
   - Add `SESSION_SECRET` (generate a random secret key)

### Required Environment Variables

Add these in Vercel Dashboard → Settings → Environment Variables:

```
SESSION_SECRET=your-random-secret-key-here
DATABASE_URL=postgresql://user:password@host:port/database (if using PostgreSQL)
```

### File Uploads

- Uploads are stored in `/tmp/uploads` on Vercel
- Files are **ephemeral** (deleted on each deployment)
- **Recommended:** Use cloud storage (AWS S3, Cloudinary, etc.) for production

## Deployment Steps

1. Push code to GitHub
2. Connect repository to Vercel
3. Vercel will automatically detect `vercel.json` and deploy
4. Add environment variables in Vercel dashboard
5. Redeploy if needed

## Troubleshooting

### 500 Error on Vercel

Common causes:
1. Missing `SESSION_SECRET` environment variable
2. Database connection issues
3. Missing dependencies in `pyproject.toml`

### Check Vercel Logs

1. Go to Vercel Dashboard → Your Project → Deployments
2. Click on the deployment
3. Check "Functions" tab for error logs

## Production Recommendations

1. **Use PostgreSQL** instead of SQLite
2. **Use cloud storage** for file uploads (S3, Cloudinary)
3. **Set up proper logging** (Vercel Logs, Sentry, etc.)
4. **Enable HTTPS** (automatic on Vercel)
5. **Set up CI/CD** (automatic with GitHub integration)

