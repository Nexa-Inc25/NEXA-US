# EAS Build Workflows

This directory contains automated workflows for building and deploying the NEXA Field Assistant app using EAS Build.

## Available Workflows

### 1. create-production-builds.yml
Simple production build workflow for both iOS and Android platforms.

**Trigger**: Manual
**Outputs**: Production builds for both platforms

### 2. development-builds.yml
Automated development builds for testing new features.

**Trigger**: Push to `develop` or `feature/*` branches
**Outputs**: Development builds with hot reload enabled

### 3. preview-testflight.yml
Creates preview builds and submits to TestFlight for beta testing.

**Trigger**: Push to `staging` or `release/*` branches
**Outputs**: 
- iOS build submitted to TestFlight
- Android APK for internal testing

### 4. production-release.yml
Complete production release pipeline with optional store submission.

**Trigger**: 
- Git tags matching `v*.*.*` pattern
- Manual workflow dispatch with submission option

**Outputs**:
- Production builds for iOS and Android
- Optional automatic submission to App Store and Google Play

### 5. ci-checks.yml
Continuous integration checks for pull requests and pushes.

**Trigger**: Pull requests and pushes to `main` and `develop`
**Checks**:
- Code linting
- TypeScript validation
- Unit tests
- As-Built API verification
- Test build creation

## Usage

### Running Workflows Locally

```bash
# Run a specific workflow
eas workflow:run create-production-builds.yml

# Run with custom parameters
eas workflow:run production-release.yml --input submit_to_stores=true
```

### GitHub Integration

1. Connect your repository to EAS:
```bash
eas github:setup
```

2. Workflows will automatically run based on their triggers:
- Push code to trigger automatic workflows
- Use GitHub Actions UI for manual workflows

### Environment Variables

Each workflow can use different environment variables:
- `EXPO_PUBLIC_ENV`: Sets the environment (development/preview/production)
- Build profiles in `eas.json` control other settings

### Monitoring Builds

```bash
# List recent builds
eas build:list

# View build details
eas build:view <build-id>

# Cancel a running build
eas build:cancel <build-id>
```

## As-Built Feature Integration

The workflows are configured to support the As-Built PDF generation feature:
- Development builds connect to local backend (`http://192.168.1.176:4000`)
- Preview builds use staging backend on Render
- Production builds use production backend

## Best Practices

1. **Branch Strategy**:
   - `develop` → Development builds
   - `staging` → Preview/TestFlight builds
   - `main` + tag → Production releases

2. **Version Management**:
   - Use semantic versioning tags (v1.0.0)
   - Auto-increment enabled for production builds

3. **Testing Flow**:
   1. Development build for local testing
   2. Preview build for TestFlight beta
   3. Production build after beta feedback
   4. Submit to stores when ready

## Troubleshooting

### Build Failures
```bash
# Check build logs
eas build:view <build-id> --log

# Validate configuration
eas config:validate
```

### Credential Issues
```bash
# Reset iOS credentials
eas credentials --platform ios --clear-credentials
```

### Workflow Errors
```bash
# Validate workflow syntax
eas workflow:validate <workflow-file>
```

## Support

- EAS Documentation: https://docs.expo.dev/eas/
- NEXA Support: support@nexa-usa.io
