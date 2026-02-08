# OAuth Implementation Analysis and Improvement Plan

## What Simon Already Fixed ✅

### 1. Nested App Context Bug (commit 8e1f9f3)
**Problem**: The `_upsert_user_from_oauth()` method was wrapped in `with self.app.app_context():`, but it's called from Flask routes that already have an active app context.

**Impact**: Nested contexts can cause database session issues, leading to "working outside of application context" errors or session state corruption.

**Fix Applied**: Removed the unnecessary `with self.app.app_context():` wrapper. Routes already provide context.

### 2. Google OAuth Nonce Missing (commit 8e1f9f3)
**Problem**: Google OAuth requires a nonce parameter for OpenID Connect security. Without it, Google may reject the authentication or the ID token validation fails.

**Impact**: OAuth login fails with cryptic errors about invalid ID tokens or missing nonce.

**Fix Applied**:
- Generate nonce in `/login/google` and store in session
- Pass nonce to `authorize_redirect()`
- Retrieve nonce in callback and pass to `parse_id_token()`

### 3. Missing Public Base URL Configuration (commits 07ec2a5, fd5cd20)
**Problem**: In production (Railway, etc.), the app needs to know its public URL to construct OAuth redirect URIs. Using Flask's `url_for(..., _external=True)` behind proxies/load balancers can generate incorrect URLs (wrong scheme, wrong hostname).

**Impact**: OAuth providers reject the callback with "redirect_uri_mismatch" errors because the redirect URI doesn't match what's registered in the OAuth provider console.

**Fix Applied**:
- Added `PLANEXE_PUBLIC_BASE_URL` environment variable
- Modified `_oauth_redirect_url()` to use public base URL when set
- Added `/api/oauth-redirect-uri` debugging endpoint to show exact redirect URI
- Documented configuration in `railway.md`

---

## Remaining Issues and Proposed Fixes 🔧

### Issue 1: No Error Handling in OAuth Callback ⚠️
**Current State**: The `/auth/<provider>/callback` route has no try/except blocks.

**Problems**:
- User denies authorization → 500 error instead of friendly message
- OAuth provider errors → Stack trace exposed to user
- Expired/invalid tokens → Confusing error page
- Network errors → Generic 500 error

**Impact**: Poor user experience, security information disclosure

**Proposed Fix**:
```python
@self.app.route('/auth/<provider>/callback')
def oauth_callback(provider: str):
    if provider not in self.oauth_providers:
        abort(404)

    try:
        client = self.oauth.create_client(provider)
        token = client.authorize_access_token()

        if provider == "google":
            nonce = session.pop("oauth_google_nonce", None)
            profile = client.parse_id_token(token, nonce=nonce)
            if not profile:
                profile = client.get("userinfo").json()
        else:
            profile = self._get_user_from_provider(provider, token)

        user = self._upsert_user_from_oauth(provider, profile)
        login_user(User(user.id, is_admin=user.is_admin))
        new_api_key = self._get_or_create_api_key(user)
        if new_api_key:
            session["new_api_key"] = new_api_key
        return redirect(url_for('account'))

    except Exception as e:
        logger.error(f"OAuth callback error for {provider}: {e}", exc_info=True)
        return render_template('login.html',
            error=f"Authentication failed. Please try again or contact support.",
            oauth_providers=self.oauth_providers,
            telegram_enabled=bool(os.environ.get("PLANEXE_TELEGRAM_BOT_TOKEN")),
            telegram_login_url=os.environ.get("PLANEXE_TELEGRAM_LOGIN_URL") or None,
        ), 401
```

### Issue 2: State Parameter for CSRF Protection ✅
**Current State**: OAuth flow uses nonce for Google. State parameter is handled automatically by authlib.

**Good News**: According to [authlib documentation](https://docs.authlib.org/en/latest/client/flask.html), authlib's Flask integration **automatically handles state parameter generation and validation** for CSRF protection. The library:
- Generates state automatically in `authorize_redirect()`
- Saves state to Flask session via `save_authorize_state()`
- Validates state in `authorize_access_token()`
- Raises `MismatchingStateError` if validation fails (Source: [authlib issue #81](https://github.com/authlib/authlib/issues/81))

**Conclusion**: No action needed. CSRF protection is already in place. ✅

### Issue 3: Missing Profile Field Validation ⚠️
**Current State**: Code assumes OAuth profiles contain expected fields like `email`, `id`, or `sub`.

**Problems**:
- Some OAuth providers don't always provide email (user can deny email scope)
- Discord may not return email if user's email is unverified
- Missing fields cause silent failures or confusing errors

**Impact**: User registration fails with unclear errors

**Proposed Fix**:
```python
def _upsert_user_from_oauth(self, provider: str, profile: dict[str, Any]) -> UserAccount:
    provider_user_id = str(profile.get("sub") or profile.get("id") or "")
    if not provider_user_id:
        raise ValueError(f"OAuth profile from {provider} missing user identifier (sub/id).")

    # Email is optional for some providers - handle gracefully
    email = profile.get("email")
    if not email:
        logger.warning(f"OAuth profile from {provider} missing email for user {provider_user_id}")

    # ... rest of method
```

### Issue 4: Code Duplication in Profile Parsing 🔍
**Current State**: Google profile parsing happens in both `oauth_callback` route and `_get_user_from_provider` method.

**Problems**:
- Code duplication makes maintenance harder
- Inconsistent logic between callback and helper method
- `_get_user_from_provider` should handle all providers uniformly

**Impact**: Maintenance burden, potential bugs if one path is updated but not the other

**Proposed Fix**: Refactor to consolidate all profile parsing in `_get_user_from_provider`:
```python
def _get_user_from_provider(self, provider: str, token: dict[str, Any], nonce: Optional[str] = None) -> dict[str, Any]:
    """Get user profile from OAuth provider."""
    client = self.oauth.create_client(provider)

    if provider == "google":
        # Try to parse ID token first (more reliable)
        profile = client.parse_id_token(token, nonce=nonce)
        if not profile:
            # Fallback to userinfo endpoint
            profile = client.get("userinfo").json()
        return profile

    if provider == "github":
        profile = client.get("user").json()
        # GitHub requires separate call for email if not public
        if not profile.get("email"):
            emails = client.get("user/emails").json()
            for item in emails:
                if item.get("primary"):
                    profile["email"] = item.get("email")
                    break
        return profile

    if provider == "discord":
        return client.get("users/@me").json()

    raise ValueError(f"Unsupported OAuth provider: {provider}")
```

Then simplify callback:
```python
@self.app.route('/auth/<provider>/callback')
def oauth_callback(provider: str):
    # ... validation and error handling

    client = self.oauth.create_client(provider)
    token = client.authorize_access_token()

    nonce = session.pop("oauth_google_nonce", None) if provider == "google" else None
    profile = self._get_user_from_provider(provider, token, nonce=nonce)

    # ... rest of logic
```

### Issue 5: Session Configuration Warning Not Enforced ℹ️
**Current State**: Code logs a warning if `SECRET_KEY` is default but continues anyway.

**Problems**:
- In production with default secret key, sessions can be hijacked (attacker can forge session cookies)
- OAuth nonces stored in session become meaningless if sessions are forgeable

**Impact**: Critical security vulnerability in production

**Proposed Fix**: Make this a hard error in production:
```python
if self.app.config.get("SECRET_KEY") == "dev-secret-key":
    if os.environ.get("FLASK_ENV") == "production" or self.public_base_url:
        raise ValueError(
            "Cannot use default SECRET_KEY in production. "
            "Set PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY environment variable."
        )
    logger.warning("Using default Flask SECRET_KEY. Set PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY for production.")
```

---

## Testing Checklist 📋

Before opening PR, test the following scenarios:

### Google OAuth
- [ ] Fresh login with new user
- [ ] Returning user login
- [ ] User denies authorization
- [ ] Redirect URI mismatch (test with wrong URL in Google Console)
- [ ] `/api/oauth-redirect-uri` returns correct URI
- [ ] Nonce validation works (try replaying callback with old nonce)

### GitHub OAuth
- [ ] Fresh login with public email
- [ ] Login with private email (requires email scope)
- [ ] User with no email address
- [ ] User denies authorization

### Discord OAuth
- [ ] Fresh login
- [ ] User with unverified email
- [ ] User denies authorization

### Security
- [ ] CSRF state validation prevents cross-site attacks
- [ ] Session cookies are secure (httponly, secure flags in production)
- [ ] No sensitive data in error messages
- [ ] Logging doesn't expose tokens or secrets

### Configuration
- [ ] Works with `PLANEXE_PUBLIC_BASE_URL` set
- [ ] Falls back correctly when `PLANEXE_PUBLIC_BASE_URL` not set (dev mode)
- [ ] Refuses to start in production with default SECRET_KEY

---

## Priority Recommendations 🎯

1. **HIGH PRIORITY**: Add error handling to OAuth callback (Issue #1) - Critical for user experience
2. **HIGH PRIORITY**: Enforce SECRET_KEY in production (Issue #5) - Critical for security
3. **MEDIUM PRIORITY**: Add profile field validation (Issue #3) - Prevents cryptic errors
4. **LOW PRIORITY**: Refactor profile parsing for consistency (Issue #4) - Code quality improvement

**RESOLVED**: Issue #2 (State parameter) - Already handled by authlib ✅

---

## Questions for Simon 💬

1. Are you seeing specific OAuth errors in production logs? (This would help prioritize fixes)
2. Is there a test environment where we can safely experiment with OAuth flows?
3. Do you have monitoring/alerts set up for OAuth failures?
4. Which OAuth providers are most important? (Google, GitHub, Discord - or focus on one first?)
5. Should we enforce the SECRET_KEY check in production, or would that break existing deployments?

---

## Additional Security Issues Found 🔒

### Issue 6: TWO Hardcoded SECRET_KEY Defaults ⚠️
**Current State**:
- `config.py` line 9: `SECRET_KEY = 'your-secret-key'`
- `app.py` line 185: Falls back to `'dev-secret-key'` if env var not set
- Current validation only checks for `'dev-secret-key'`, missing the config.py default

**Problems**:
- `config.py` is loaded first, so `'your-secret-key'` is the actual default used
- Anyone can forge session cookies with this known value
- OAuth nonces in session become worthless (attacker can replay attacks)

**Impact**: CRITICAL - Session hijacking in production

**Validation**: ✅ CONFIRMED - [config.py:9](c:\Projects\PlanExe2026\frontend_multi_user\src\config.py:9) has `SECRET_KEY = 'your-secret-key'`

### Issue 7: Missing Session Cookie Security Flags ⚠️
**Current State**: No session cookie security configuration

**Problems**:
- `SESSION_COOKIE_SECURE` not set → Cookies sent over HTTP (interceptable)
- `SESSION_COOKIE_HTTPONLY` not set → JavaScript can access cookies (XSS vulnerability)
- `SESSION_COOKIE_SAMESITE` not set → Cookies sent in cross-site requests (CSRF vulnerability)

**Impact**: HIGH - Cookie theft via XSS, man-in-the-middle attacks

**Validation**: ✅ CONFIRMED - No SESSION_COOKIE settings found in codebase

**Proposed Fix**:
```python
# In config.py or app.py config loading
SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production' or bool(os.environ.get('PLANEXE_PUBLIC_BASE_URL'))
SESSION_COOKIE_HTTPONLY = True  # Always protect from XSS
SESSION_COOKIE_SAMESITE = 'Lax'  # Prevent CSRF while allowing OAuth redirects
```

### Issue 8: No CSRF Protection on Admin Login Form ⚠️
**Current State**: [login.html:61-67](c:\Projects\PlanExe2026\frontend_multi_user\templates\login.html:61) form has no CSRF token

**Problems**:
- Attacker can create malicious page that submits login form to victim's browser
- While authlib handles OAuth CSRF via state parameter, admin login is unprotected

**Impact**: MEDIUM - CSRF attack on admin login (requires social engineering)

**Validation**: ✅ CONFIRMED - Login form POST has no CSRF token

**Proposed Fix**:
- Option A: Use Flask-WTF for automatic CSRF protection
- Option B: Manual CSRF token generation and validation

**Note**: This is lower priority than cookie flags because:
1. Attack requires convincing admin to visit malicious site
2. Admin credentials must already be known to attacker
3. OAuth login paths are already protected by authlib state parameter

### Issue 9: Nonce Parameter Inconsistency 🔍
**Current State**: [_get_user_from_provider:428-434](c:\Projects\PlanExe2026\frontend_multi_user\src\app.py:428) calls `parse_id_token(token)` without nonce parameter

**Problems**:
- Method signature doesn't accept nonce
- If ever called for Google (currently isn't), would fail validation
- Code duplication between callback and helper method

**Impact**: LOW - Not currently used for Google, but creates confusion

**Validation**: ✅ CONFIRMED - Method doesn't have nonce parameter

**Fix**: Already covered in Issue #4 (code duplication refactor)

---

## Revised Priority Recommendations 🎯

### CRITICAL (Must Fix Before Production)
1. **Issue #6**: Fix BOTH SECRET_KEY defaults - check for `'your-secret-key'` AND `'dev-secret-key'`
2. **Issue #7**: Add session cookie security flags - prevents session hijacking

### HIGH (User Experience + Security)
3. **Issue #1**: Add error handling to OAuth callback - prevents ugly 500 errors
4. **Issue #3**: Add profile field validation - clearer error messages

### MEDIUM (Security Hardening)
5. **Issue #8**: Add CSRF to admin login form - defense in depth
6. **Issue #5**: Enforce SECRET_KEY check at startup - fail-fast protection

### LOW (Code Quality)
7. **Issue #4**: Refactor profile parsing - eliminates duplication (includes Issue #9)

---

## Implementation Plan 📝

### Phase 1: Critical Security Fixes (Must Do)
**Estimated time: 30 minutes**

1. **Fix SECRET_KEY validation** ([app.py:189-190](c:\Projects\PlanExe2026\frontend_multi_user\src\app.py:189))
   ```python
   secret_key = self.app.config.get("SECRET_KEY")
   is_default_key = secret_key in ("dev-secret-key", "your-secret-key", None)
   is_production = os.environ.get("FLASK_ENV") == "production" or bool(self.public_base_url)

   if is_default_key:
       if is_production:
           raise ValueError(
               "Cannot use default SECRET_KEY in production. "
               "Set PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY environment variable. "
               "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
           )
       logger.warning(
           "Using default Flask SECRET_KEY (%s). "
           "Set PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY for production.",
           secret_key
       )
   ```

2. **Add session cookie security** (in [app.py:184-187](c:\Projects\PlanExe2026\frontend_multi_user\src\app.py:184) after config loading)
   ```python
   # Session security settings
   is_production = os.environ.get("FLASK_ENV") == "production" or bool(self.public_base_url)
   self.app.config.setdefault('SESSION_COOKIE_SECURE', is_production)
   self.app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
   self.app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
   logger.info(f"Session cookie security: secure={is_production}, httponly=True, samesite=Lax")
   ```

3. **Update .env examples** to show SECRET_KEY generation
   ```bash
   # Generate secure secret key with:
   # python -c 'import secrets; print(secrets.token_hex(32))'
   PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY='your-generated-key-here'
   ```

**Testing**:
- Start app without SECRET_KEY → Should fail in production, warn in dev
- Verify session cookies have Secure flag in production
- Verify cookies have HttpOnly and SameSite flags always

### Phase 2: Error Handling (High Priority)
**Estimated time: 45 minutes**

1. **Wrap OAuth callback in try/except** ([app.py:656-674](c:\Projects\PlanExe2026\frontend_multi_user\src\app.py:656))
   - Catch `OAuthError` (user denies)
   - Catch `MismatchingStateError` (CSRF attempt)
   - Catch general exceptions
   - Redirect to login with user-friendly error message

2. **Add error parameter to login.html**
   - Display error message if present
   - Style appropriately (Bootstrap alert-danger)

3. **Add profile validation** in `_upsert_user_from_oauth`
   - Check for missing `sub`/`id`
   - Log warning if email missing
   - Raise clear exception if user ID missing

**Testing**:
- Deny OAuth authorization → See friendly error
- Tamper with state parameter → See security error
- Test with missing email scope → See logged warning

### Phase 3: CSRF Protection (Medium Priority)
**Estimated time: 1 hour**

**Option A: Flask-WTF (Recommended)**
- Add `flask-wtf` to dependencies
- Enable CSRF protection globally
- Add `{{ form.csrf_token }}` to login form

**Option B: Manual CSRF tokens**
- Generate token on GET /login
- Store in session
- Validate on POST /login

**Decision needed**: Which approach fits project better?

### Phase 4: Code Refactoring (Low Priority)
**Estimated time: 1 hour**

1. **Consolidate profile parsing** in `_get_user_from_provider`
   - Add optional `nonce` parameter
   - Move Google logic from callback to helper
   - Simplify callback route

**Testing**: Verify all three providers (Google, GitHub, Discord) still work

---

## Environment Configuration Changes 📋

### .env.docker-example and .env.developer-example
Add documentation and examples:

```bash
# Flask session security (REQUIRED for production)
# Generate with: python -c 'import secrets; print(secrets.token_hex(32))'
PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY='your-generated-secret-key-here'

# Optional: Set FLASK_ENV=production to enforce security checks
# FLASK_ENV='production'
```

### config.py Changes
**Option 1: Remove default SECRET_KEY** (Breaking change - requires env var)
```python
SECRET_KEY = os.environ.get('PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY required")
```

**Option 2: Keep default but improve validation** (Non-breaking)
```python
SECRET_KEY = 'your-secret-key'  # Validated at startup - will fail in production
```

**Recommendation**: Option 2 (non-breaking) + runtime validation in app.py

---

## Risk Assessment 🚨

### Breaking Changes
None of the Phase 1-2 changes are breaking for existing deployments:
- SECRET_KEY check only fails if `FLASK_ENV=production` OR `PLANEXE_PUBLIC_BASE_URL` is set
- Session cookie flags don't break existing sessions
- Error handling only improves UX

### Deployment Considerations
- **Railway/production**: Must set `PLANEXE_FRONTEND_MULTIUSER_SECRET_KEY` before deploying
- **Local dev**: Works as-is with warning logged
- **Testing**: Need OAuth credentials for all three providers

### Migration Path
1. Deploy Phase 1 changes
2. Monitor logs for SECRET_KEY warnings
3. Update production env vars
4. Deploy remaining phases

---

## Open Questions ❓

1. **CSRF Protection**: Flask-WTF or manual implementation?
2. **Rate Limiting**: Should we add this (Issue #9 from competing dev)? Requires additional library (Flask-Limiter)
3. **Account Linking**: Should we link accounts by email (Issue #11)? This is a feature, not a bug fix
4. **Token Storage**: Should we store OAuth tokens for future API calls (Issue #14)? Requires database schema changes

---

## References 📚

- [Authlib Flask OAuth Client Documentation](https://docs.authlib.org/en/latest/client/flask.html)
- [Authlib OAuth2 Session Documentation](https://docs.authlib.org/en/latest/client/oauth2.html)
- [Authlib Issue #81: MismatchingStateError](https://github.com/authlib/authlib/issues/81)
- [Authlib Issue #376: CSRF State Validation](https://github.com/authlib/authlib/issues/376)
- [Flask Session Cookie Documentation](https://flask.palletsprojects.com/en/3.0.x/config/#SESSION_COOKIE_SECURE)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
