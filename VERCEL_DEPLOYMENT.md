# Vercel Deployment Guide for Vertex AI Image Recognition Tester

This guide will walk you through deploying your Vertex AI Image Recognition Tester to Vercel.

## 🚀 Quick Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/vertex-ai-image-tester)

## 📋 Prerequisites

- [Vercel account](https://vercel.com/signup)
- [Git](https://git-scm.com/) installed
- [Node.js](https://nodejs.org/) (for Vercel CLI)
- Google Cloud Project with Vertex AI enabled

## 🔧 Step-by-Step Deployment

### 1. Install Vercel CLI

```bash
npm i -g vercel
```

### 2. Login to Vercel

```bash
vercel login
```

### 3. Deploy Your Project

Navigate to your project directory and run:

```bash
vercel
```

Follow the prompts:
- Set up and deploy? `Y`
- Which scope? `[Select your account]`
- Link to existing project? `N`
- What's your project's name? `vertex-ai-image-tester`
- In which directory is your code located? `./`
- Want to override the settings? `N`

### 4. Configure Environment Variables

After deployment, you need to set your Google Cloud environment variables:

```bash
vercel env add GOOGLE_CLOUD_PROJECT
vercel env add VERTEX_ENDPOINT_ID
vercel env add VERTEX_LOCATION
```

Or set them in the Vercel dashboard:
1. Go to your project in [Vercel Dashboard](https://vercel.com/dashboard)
2. Click on your project
3. Go to Settings → Environment Variables
4. Add the following variables:

| Variable | Value | Environment |
|----------|-------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Your Google Cloud Project ID | Production, Preview, Development |
| `VERTEX_ENDPOINT_ID` | Your Vertex AI endpoint ID | Production, Preview, Development |
| `VERTEX_LOCATION` | Your Vertex AI location (e.g., `europe-west4`) | Production, Preview, Development |

### 5. Set Up Google Cloud Authentication

#### Option A: Service Account Key (Recommended)

1. **Create a service account** in Google Cloud Console:
   ```bash
   gcloud iam service-accounts create vertex-ai-tester \
     --display-name="Vertex AI Tester"
   ```

2. **Grant necessary roles**:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:vertex-ai-tester@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```

3. **Create and download a key**:
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=vertex-ai-tester@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Set the credentials** in Vercel:
   ```bash
   vercel env add GOOGLE_APPLICATION_CREDENTIALS
   # Enter the path to your key.json file
   ```

#### Option B: Application Default Credentials

If you're using `gcloud auth application-default login`, you can set:

```bash
vercel env add GOOGLE_APPLICATION_DEFAULT_CREDENTIALS
```

### 6. Redeploy with Environment Variables

```bash
vercel --prod
```

## 🌐 Access Your Deployed App

After successful deployment, Vercel will provide you with:
- **Production URL**: `https://your-project.vercel.app`
- **Preview URLs**: For each git push/PR

## 🔍 Testing Your Deployment

1. **Visit your deployed URL**
2. **Upload an image** using the file picker or drag & drop
3. **Adjust parameters** as needed
4. **Click "Run Detection"** to test your Vertex AI endpoint

## 📁 Project Structure for Vercel

```
vertex-ai-image-tester/
├── api/                    # Serverless functions
│   ├── upload.py          # Image processing endpoint
│   └── requirements.txt   # Python dependencies
├── static/                 # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── index.html             # Main page (served as static)
├── vercel.json            # Vercel configuration
└── README.md
```

## ⚙️ Vercel Configuration Details

### `vercel.json` Breakdown

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/*.py",
      "use": "@vercel/python"        // Python runtime
    },
    {
      "src": "static/**",
      "use": "@vercel/static"        // Static file serving
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/$1"              // API routes
    },
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"           // Static assets
    },
    {
      "src": "/(.*)",
      "dest": "/index.html"          // SPA routing
    }
  ],
  "functions": {
    "api/upload.py": {
      "maxDuration": 30              // 30 second timeout
    }
  }
}
```

## 🚨 Important Notes

### Function Timeout
- Vercel serverless functions have a **30-second timeout**
- Large images may take longer to process
- Consider image compression for better performance

### Cold Starts
- First request to your API may be slower
- Subsequent requests will be faster
- Consider using Vercel Pro for better performance

### File Size Limits
- Vercel has a **4.5MB payload limit** for serverless functions
- Your app handles this with client-side validation
- Consider implementing image compression if needed

## 🔧 Customization

### Adding New API Endpoints

1. Create new Python files in the `api/` directory
2. Follow the same pattern as `upload.py`
3. Update `vercel.json` if needed

### Modifying the Frontend

- Edit `index.html` for HTML changes
- Modify `static/css/style.css` for styling
- Update `static/js/app.js` for functionality

### Environment-Specific Configurations

You can set different environment variables for different environments:

```bash
vercel env add GOOGLE_CLOUD_PROJECT production
vercel env add GOOGLE_CLOUD_PROJECT preview
vercel env add GOOGLE_CLOUD_PROJECT development
```

## 🐛 Troubleshooting

### Common Issues

1. **Environment Variables Not Working**
   - Ensure variables are set for all environments
   - Redeploy after setting environment variables
   - Check Vercel dashboard for variable status

2. **API Endpoint Not Found**
   - Verify `vercel.json` configuration
   - Check that `api/upload.py` exists
   - Ensure proper file structure

3. **Authentication Errors**
   - Verify Google Cloud credentials
   - Check service account permissions
   - Ensure environment variables are correct

4. **Function Timeout**
   - Optimize image processing
   - Consider image compression
   - Check Vercel function logs

### Debug Mode

Enable debug logging in Vercel:

```bash
vercel logs your-project-name
```

### Local Development

Test locally before deploying:

```bash
vercel dev
```

## 📈 Performance Optimization

### For Production

1. **Enable Vercel Analytics**:
   ```bash
   vercel analytics
   ```

2. **Use Vercel Pro** for:
   - Longer function timeouts
   - Better cold start performance
   - Advanced caching

3. **Implement Caching**:
   - Cache processed images
   - Store prediction results
   - Use CDN for static assets

## 🔄 Continuous Deployment

### Automatic Deployments

1. **Connect your GitHub repository** to Vercel
2. **Push changes** to trigger automatic deployments
3. **Preview deployments** for pull requests
4. **Production deployments** for main branch

### Deployment Commands

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod

# Deploy specific branch
vercel --prod --target=staging
```

## 📞 Support

- **Vercel Documentation**: [vercel.com/docs](https://vercel.com/docs)
- **Vercel Support**: [vercel.com/support](https://vercel.com/support)
- **Google Cloud Support**: [cloud.google.com/support](https://cloud.google.com/support)

## 🎉 Success!

Once deployed, your Vertex AI Image Recognition Tester will be available at your Vercel URL. Users can:

- Upload images via drag & drop or file picker
- Adjust detection parameters in real-time
- View annotated results with bounding boxes
- See object counts and class distributions
- Experience fast, responsive performance

Your app is now running on Vercel's global edge network! 🚀