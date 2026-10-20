# Spotify sign-in and Developer API setup (macOS)

Use only accounts and content you are authorized to access. Do not post passwords, cookies, authorization links/codes, tokens, credential JSON, or screenshots containing them in chat, GitHub issues, shell history, or commits.

## Two separate authentication flows

| Use | What you need | Local credential file |
| --- | --- | --- |
| Zotify Login5 / streaming session | Browser sign-in through the built-in upstream client; no key to obtain | `~/Library/Application Support/Zotify/credentials.json` by default |
| Zotify optional Web API access | Your Spotify app's Client ID and PKCE browser consent; no Client Secret in this flow | `~/Library/Application Support/Zotify/api_credentials.json` by default |
| Companion Music Manager | Its own Spotipy setup, including Client ID and Client Secret | Manager's Spotipy cache |

A Developer Dashboard Client ID does not replace Zotify's Login5 sign-in or grant streaming/download rights. The manager's Client Secret and Spotipy cache are not used by Zotify; do not copy or rename credential files between the projects.

## First Zotify sign-in

1. Install this fork using [INSTALLATION.md](../INSTALLATION.md).
2. Run Zotify for one specific item you intend to download, for example:

   ```zsh
   "$HOME/zotify/.venv/bin/zotify" 'https://open.spotify.com/track/TRACK_ID'
   ```

3. If Login5 browser authorization is required, Zotify prints an authorization link. Open it on the same Mac, verify the account and permissions, and approve the request yourself. Keep the CLI running while the browser returns to the local callback, normally `http://127.0.0.1:4381/login`.
4. Wait for the CLI to report a successful authenticated query and download. An opened page or a created credential file alone does not confirm a usable session.

By default, `config.json` and credentials saved after successful browser authorization live under `~/Library/Application Support/Zotify/`. Credentials are local JSON and are not encrypted by this project. Restrict access to your Mac account and keep them out of repositories and backups shared with others. If you use alternate locations, pass the relevant location options on each invocation; alternate paths are not remembered automatically.

Login5 behavior comes from the pinned upstream library. A new Developer API app will not fix rejection of the built-in Login5 client. If authorization fails, stop and diagnose the redacted error rather than replacing identifiers, extracting cookies, or repeatedly retrying.

## Optional: create a Spotify Developer app for Web API access

A personal app is only needed if you want Zotify's optional custom Web API OAuth integration. Spotify's current dashboard labels, account eligibility, development-mode user requirements, quotas, and endpoint access can change; follow the live [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) policy.

1. Sign in to your developer account and create an app for personal use. Supply the required app name, description, and website fields, then enable Web API if the Dashboard asks.
2. In the app's redirect settings, register exactly `http://127.0.0.1:4381/login` and save.
3. Copy the **Client ID**. This PKCE flow does not use the Client Secret.
4. If the app is in development mode, add the Spotify account you use where the Dashboard requires it.
5. Add the following values to `config.json` in `~/Library/Application Support/Zotify/` (preserve all other settings):

   ```json
   {
     "API_CLIENT_ID": "YOUR_DEVELOPER_APP_CLIENT_ID",
     "API_CLIENT_LEGACY": false
   }
   ```

   If the config file does not exist yet, create its parent directory and a valid JSON file before launching Zotify. Do not paste the ID in a public issue. A Client ID is an identifier, but treat your account's associated app settings as private.
6. Run Zotify again. The optional Web API flow can request a separate browser consent and saves its OAuth state to `api_credentials.json` by default.

A custom app does not grant every endpoint permission and does not substitute for Login5. If you share the app with the manager, register its distinct callback (`http://127.0.0.1:9090` by default) as a second redirect and follow the [manager authentication guide](https://github.com/The-Rinzler/Zotify-MacOS-Music-Manager/blob/main/docs/AUTHENTICATION.md). Do not replace Zotify's callback with the manager's callback.

## Redirect and network precautions

The registered redirect must match exactly; scheme, address, port, path, and trailing slash matter. The current Spotify redirect rules permit HTTP for explicit loopback IP addresses; `localhost` is not an equivalent substitute. Use the CLI and browser on the same Mac.

**Inherited limitation:** Zotify's OAuth helper calls `set_listen_all(True)`. Although the advertised redirect is loopback, the pinned library's callback server binds all interfaces. Do not expose or forward port 4381, and do not authorize over an untrusted network. This guide does not claim the callback listener is loopback-only.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| `client_id: Invalid` / `INVALID_CLIENT` | Identify whether Login5 or custom Web API failed. Check your Developer app ID and redirect only for the custom API flow; it cannot replace the built-in Login5 client. |
| Login5 error `1` / `INVALID_CREDENTIALS` | Stop. A cache can exist even if session setup failed. Redact the error and reauthorize only after diagnosing the account/client state. |
| Redirect mismatch or callback timeout | Verify the exact Dashboard redirect, use the same Mac for browser and CLI, ensure the port is free, and leave the CLI running. The default timeout is 120 seconds. |
| HTTP 401 / 403 | Check account/app consent, permissions, development-mode allowlist, and endpoint restrictions. A valid Client ID does not guarantee access to every endpoint. |
| HTTP 429 | This is rate limiting, not an empty playlist. Stop repeated requests and honor Spotify's Retry-After/backoff guidance. |
| Unexpected version or import path | Run the explicit `.venv/bin/zotify` executable and clear `PYTHONPATH`/`PYTHONHOME`; inspect `zotify.config.__file__` from outside older checkouts. |

If a credential is exposed, revoke app access in your Spotify account settings, rotate an exposed Client Secret in the Dashboard, and remove the secret from Git history before publishing. For support, share only the version/commit, flow name, HTTP/error code, and redacted messages; strip tokens and OAuth callback query strings.

## Official references

- [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- [Redirect URI requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)
- [Authorization Code with PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
- [Web API quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)