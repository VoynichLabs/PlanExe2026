# Railway Configuration for `frontend_multi_user`

```
PLANEXE_FRONTEND_MULTIUSER_ADMIN_PASSWORD="insert-your-password"
PLANEXE_FRONTEND_MULTIUSER_ADMIN_USERNAME="insert-your-username"
PLANEXE_FRONTEND_MULTIUSER_PORT="5000"
PLANEXE_FRONTEND_MULTIUSER_DB_HOST="database_postgres"
PLANEXE_POSTGRES_PASSWORD="${{shared.PLANEXE_POSTGRES_PASSWORD}}"
PLANEXE_OAUTH_GOOGLE_CLIENT_ID='insert-your-clientid'
PLANEXE_OAUTH_GOOGLE_CLIENT_SECRET='insert-your-secret'
PLANEXE_PUBLIC_BASE_URL='https://home.planexe.org'
PLANEXE_STRIPE_SECRET_KEY='insert-your-secret'
```

## OAuth (Google) in production

For "Sign in with Google" to work, two things must match exactly:

1. **Railway env:** Set `PLANEXE_PUBLIC_BASE_URL` to your public URL with no trailing slash, e.g. `https://home.planexe.org`. The app uses it to build the redirect URI: `{PLANEXE_PUBLIC_BASE_URL}/auth/google/callback`.

2. **Google Cloud Console:** In your OAuth 2.0 Client (APIs & Services → Credentials → your OAuth client), under **Authorized redirect URIs**, add the **exact** URI your app uses. To see what the app sends, open:
   ```
   https://home.planexe.org/api/oauth-redirect-uri
   ```
   Copy the single line it returns and add that string to **Authorized redirect URIs** (one line, no trailing slash). Use the OAuth client type **Web application** and the client ID that matches `PLANEXE_OAUTH_GOOGLE_CLIENT_ID`. Save. If you still see "redirect_uri_mismatch", the URI in Google must match the debug URL output character-for-character.

## Volume - None

The `frontend_multi_user` gets initialized via env vars, and doesn't write to disk, so it needs no volume.

## Domain

Configure a `Custom Domain` named `home.planexe.org`, that points to railway.
Incoming traffic on port 80 gets redirect to target port 5000.
