# TTD Bot Deployment Guide

## Overview
This guide will help you deploy the TTD Bot with:
- **Backend**: Render (with Docker)
- **Frontend**: Vercel

The bot maintains its full visual functionality using a virtual display (Xvfb) on Render.

## Prerequisites
1. GitHub account
2. Render account (free tier available)
3. Vercel account (free tier available)
4. Git installed on your local machine

## Step 1: Prepare Your Repository

1. Initialize git repository (if not done):
```bash
git init
git add .
git commit -m "Initial commit"
```

2. Create a new repository on GitHub and push your code:
```bash
git remote add origin https://github.com/yourusername/ttd-bot.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy Backend on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `ttd-bot-backend`
   - **Environment**: `Docker`
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Dockerfile Path**: `./Dockerfile`

5. Add Environment Variables:
   ```
   PORT=8000
   DISPLAY=:99
   FRONTEND_ORIGINS=https://your-frontend-domain.vercel.app
   TTD_CONFIG_PATH=/app/srivari_group_data.json
   ADMIN_PASSWORD=your_secure_password
   ```

6. Click "Create Web Service"

7. Wait for deployment to complete (5-10 minutes)

8. Note your backend URL: `https://your-app-name.onrender.com`

## Step 3: Deploy Frontend on Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your GitHub repository
4. Configure the project:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

5. Add Environment Variables:
   ```
   VITE_API_BASE=https://your-render-backend-url.onrender.com
   ```

6. Click "Deploy"

7. Note your frontend URL: `https://your-frontend.vercel.app`

## Step 4: Update CORS Configuration

1. Go back to Render Dashboard
2. Open your backend service
3. Go to Environment tab
4. Update `FRONTEND_ORIGINS` with your actual Vercel URL:
   ```
   FRONTEND_ORIGINS=https://your-actual-frontend.vercel.app,http://localhost:5173
   ```
5. Save and redeploy

## Step 5: Update Frontend API URL

1. In your Vercel dashboard, go to your project
2. Go to Settings → Environment Variables
3. Update `VITE_API_BASE` with your actual Render URL:
   ```
   VITE_API_BASE=https://your-actual-backend.onrender.com
   ```
4. Redeploy the frontend

## Step 6: Test Your Deployment

1. Visit your Vercel URL
2. Try opening the browser from the web interface
3. Check that the bot can interact with the TTD website
4. Test the auto-fill functionality

## Important Notes

### Bot Functionality
- ✅ Bot maintains full visual functionality
- ✅ Chrome runs with virtual display (Xvfb)
- ✅ Manual login and navigation still required
- ✅ Auto-fill works exactly as before
- ✅ File uploads and downloads supported

### Render Configuration
- Uses Docker for consistent environment
- Virtual display enables Chrome GUI
- Persistent storage for Chrome profile
- Auto-scaling disabled (maintains session)

### Security
- Authentication can be enabled via `ADMIN_PASSWORD`
- CORS properly configured for your frontend
- Sensitive data redacted in logs

### Limitations
- Render free tier sleeps after 15 min of inactivity
- Chrome profile resets on container restart
- Limited to single concurrent user

## Troubleshooting

### Backend Issues
1. Check Render logs: Dashboard → Service → Logs
2. Verify environment variables are set
3. Ensure Dockerfile builds successfully

### Frontend Issues
1. Check Vercel build logs
2. Verify API_BASE environment variable
3. Check browser network tab for CORS errors

### Bot Issues
1. Check if Chrome starts successfully in logs
2. Verify virtual display is running
3. Test locally first with same configuration

## Custom Domain (Optional)

### For Backend (Render)
1. Go to Settings → Custom Domains
2. Add your domain and configure DNS

### For Frontend (Vercel)
1. Go to Settings → Domains
2. Add your domain and configure DNS

## Support

If you encounter issues:
1. Check the logs on both platforms
2. Verify all URLs are correctly configured
3. Test the local version first
4. Ensure Chrome can run in the cloud environment