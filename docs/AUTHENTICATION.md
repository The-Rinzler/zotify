# Spotify authentication and Developer API keys (macOS)

Return to the [README](../README.md) for setup and isolated smoke commands.
Do not paste passwords, cookies, authorization URLs/codes, tokens, or credential
JSON into chat, GitHub issues, screenshots, commits, or shell command lines.

## Three identities—do not mix their files

| Workflow | What you supply | Local state |
| --- | --- | --- |
| Zotify Login5 / streaming session | Browser sign-in using the upstream built-in client | `credentials.json`, or your explicit `--credentials-location` |
| Zotify optional Developer API | Your app's **Client ID**; PKCE, no Client Secret | `api_credentials.json`, or explicit `--api-credentials-location` |
| Companion Manager / Spotipy | Your app's **Client ID and Client Secret**, separate browser consent | Its Spotipy cache (currently `~/.cache-spotipy`) |

A developer app provides Web API access; it does **not** replace the separate
Login5 session or grant streaming/download rights. A Spotipy token is not a
Login5 credential. Do not copy/rename caches between the projects. Zotify does not
read the manager's `SPOTIPY_*` variables.

## 1. Login5: browser sign-in, no keys to extract

1. Install this checkout using [INSTALLATION.md](../INSTALLATION.md).
2. Use the README's fresh test directory and **all explicit isolation flags**.
   Run the metadata-only `zotify_smoke --test 'YOUR_PLAYLIST_URL'` command.
3. Open the printed Spotify authorization link on the **same Mac** as the
   running CLI. Inspect the account and permissions; sign in and approve yourself.
4. The default callback is `http://127.0.0.1:4381/login`. Leave the terminal
   running while the browser redirects back. Zotify prints a link; it does not
   require you to extract a browser cookie or manually harvest a token.
5. Require a successful authenticated query. An opened page, saved cache, or
   browser success message alone is insufficient proof of a usable session.

The built-in Login5 client and Spotify's authentication behavior are inherited
from the pinned upstream library. If Spotify rejects that client, creating a new
developer app does **not** automatically fix it. Stop and diagnose the redacted
error rather than replacing client IDs, fabricating a key, or repeatedly retrying.
This release-preparation work does not claim a live Login5 fix.

## 2. Optional: create your own Developer API app

Start at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
Dashboard policy and labels can change. App creation, development-mode users,
account requirements and endpoint access depend on Spotify's current policies;
follow the live Dashboard rather than assuming a key guarantees access.

1. Sign in to your own developer account. Create an app for personal use; supply
   its name, description and required website field if prompted. Select Web API.
2. In the app's settings, register **exactly**:
   `http://127.0.0.1:4381/login`.
3. Save the settings and copy the **Client ID**. The Client ID is an identifier,
   not a streaming token. This Zotify PKCE flow does **not** need the Client Secret.
4. If using development mode, add/authorize the Spotify account you will use
   where the Dashboard requires it. Spotify can restrict endpoints even after
   authorization succeeds.
5. In your private **test** `config.json`, merge these keys without deleting the
   sample's MP3/layout settings:

   ```json
   {
     "API_CLIENT_ID": "YOUR_DEVELOPER_APP_CLIENT_ID",
     "API_CLIENT_LEGACY": false
   }
   ```

   This fragment is not a replacement for the whole sample configuration.
   Do not assume a newly created app has legacy endpoint access.
6. Repeat the README's isolated command. Login5 and custom API OAuth are separate
   flows and may each request browser consent. Save Developer API OAuth state
   only at the explicit `--api-credentials-location` test path.

If sharing this one app with the manager, also register its **different** exact
callback (`http://127.0.0.1:9090` by default). Keep both redirect registrations;
do not change Zotify's callback to the manager's. Follow the
[manager's authentication guide](https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager/blob/main/docs/AUTHENTICATION.md)
for its Client Secret and cache. On an unmerged review, select its PR branch if
the guide is not on `main` yet.

## 3. Redirect rules and local-network caution

Spotify requires an exact registered redirect match. Explicit loopback IPs may
use HTTP; `localhost` is not a supported substitute under the current redirect
rules. The scheme, port, path and trailing slash matter. Do not use a remote
browser against a loopback callback unless you understand and explicitly arrange
a secure tunnel; the supported guide assumes CLI and browser on the same Mac.

**Inherited limitation:** Zotify's `create_oauth()` calls `set_listen_all(True)`.
Although it advertises a loopback redirect, the pinned library's callback server
binds all interfaces. Do not expose/forward port 4381 or authorize on an untrusted
network. This guide does not claim that the callback listener is loopback-only.
Use a trusted local machine/network and inspect the consent request. Listener
hardening is separate from these documentation/setup changes.

## 4. Protect and reset only the intended credentials

For test runs, use `umask 077` before creating caches and `chmod 700 "$TEST"` on
the test directory. Credential files are stored locally as JSON, **not** encrypted
by this project. Restrict their permissions; keep them outside the Git checkout.
The setup script never migrates or deletes them. `.gitignore` is a backup guard,
not a substitute for inspecting what you stage.

Default macOS files live under `~/Library/Application Support/Zotify/` unless
configured otherwise. Specifying `--config-location` alone does not guarantee
both credential paths and archive roots are isolated: keep **all** explicit test
flags on every invocation.

To reauthorize a **test** identity, stop Zotify, move only that identity's test
cache aside as a private backup, then repeat its browser flow. Do not delete the
production config or both caches indiscriminately. Revoke app access in your
Spotify account settings if a real token was exposed, rotate an exposed Client
Secret in the developer Dashboard, and purge the leaked secret from Git history
before publishing. Uninstalling the package does not remove account caches.

## Troubleshooting

| Symptom | Check / next step |
| --- | --- |
| `client_id: Invalid` / `INVALID_CLIENT` | Identify which flow printed the error. Check your Developer API app ID and redirect if that flow failed; do not substitute it for the built-in Login5 client. |
| Login5 error `1` / `INVALID_CREDENTIALS` | A cache can exist even after session setup failed. Stop, retain a redacted error, and reauthorize only an isolated test identity if appropriate. Do not repeatedly retry production credentials. |
| Redirect mismatch / callback timeout | Exact Dashboard redirect; browser on same Mac; port not occupied; terminal still running. Default timeout is 120 seconds. |
| HTTP 401 / 403 | Account/app authorization, permissions, dev-mode allowlist or endpoint restrictions. A valid Client ID does not guarantee every endpoint. |
| HTTP 429 | Rate limited, **not an empty playlist**. Stop requests and honor Spotify's Retry-After/backoff; do not hammer retry. |
| Wrong version or import path | Use the explicit new `.venv/bin/zotify` and clear `PYTHONPATH`/`PYTHONHOME`; inspect `zotify.config.__file__` from outside old checkouts. |

For support, share only version/commit, flow name, HTTP/error code and redacted
messages. Strip tokens, credential bodies and OAuth callback query strings.

## Official references

- [Developer Dashboard](https://developer.spotify.com/dashboard)
- [Redirect URI requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)
- [Authorization Code with PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
- [Web API quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)

Live Spotify authorization and one real download remain Mac acceptance checks;
offline tests do not prove either.
