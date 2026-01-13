# Fly.io Deployment Guide

## Prerequisites
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
fly auth login
```

## Dataset (~28MB)

The dataset is included in the Docker image automatically. No additional configuration needed!

## Deploy

### Initial Setup
```bash
# Create the app and deploy
fly launch

# Or manually:
fly launch --no-deploy
fly deploy
```

### Check Status
```bash
fly status
fly logs
```

### Access Your App
```bash
# Get the app URL
fly info

# Test WebSocket
# wss://your-app.fly.dev/ws
```

## Configuration

Edit `fly.toml` to customize:
- `app`: Your app name
- `primary_region`: Closest region to your users
- `memory`: Increase if needed (2GB default)
- Environment variables

## Costs
- Fly.io free tier: 3 shared-cpu VMs with 256MB RAM
- For PhantomLink (2GB RAM): ~$15-20/month
- Volume storage: ~$0.15/GB/month

## WebSocket Configuration
WebSocket connections are automatically supported through the `tcp` service configuration in `fly.toml`. No additional setup needed.
