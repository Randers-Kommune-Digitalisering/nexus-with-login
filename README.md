# Vue/Flask app for custom Nexus content
This app handles Nexus login and user management and displays custom content and interactions.

**Note:** Automatic testing, building, and production deployment occur only when
a version tag (`v*.*.*`) is pushed and its commit is on `main`. The Docker image
and deployment use the exact tag (including `v`). The separate manual build
workflow is still available.

## Run frontend and backend in Docker
* Run ```docker-compose up``` from the repository root.
* Backend runs on port 8080; frontend runs on port 3000.

## Run the frontend (Vue)
* Change to the Vue directory: ```cd vue```
* Install dependencies: ```npm install```
* Build, hot-reload, and start the frontend: ```npm run dev```

## Run the backend (Python)
* Start the development server: ```python flask/src/main.py```

The production Docker image serves `main:app` with Gunicorn on `PORT` (default
8080). It uses one worker with eight threads. Requests from different sessions
and health checks can run concurrently; requests sharing a session are serialized
from session load through save so refresh-token rotation and session writes cannot
race. If a session is busy, the server responds with 503 and `Retry-After: 1`
without waiting on the worker thread. Vue queues its own requests and retries
that specific response for a bounded period; requests from other tabs may still
need to be retried. Keep one worker and one replica with this in-process lock and filesystem
session store; scaling either requires a shared session store and cross-process
coordination. Gunicorn access logs remain disabled because they could contain
patient identifiers.

## Development commands
* Build a Docker image: ```docker build -t vue-python-template .```
* Run the image: ```docker run -p 8080:8080 vue-python-template```
* Lint: ```flake8 python/src tests --count --select=E9,F63,F7,F82 --show-source --statistics```
* Unit tests: ```pytest```

## Nexus API from Vue

Vue checks `GET /user/session` on page load; it returns only an authentication
boolean and does not cache the response. Only authenticated sessions request
`GET /api/home-ressource` to fetch the
Nexus home resource. Other HAL links under the configured `BASE_URL` and `BASE_PATH`
can be requested through
`/api/nexus/<path>` with GET, POST, or PUT. Resolve relative links against the Nexus
URL of the response that supplied them, then send the path and query to the local
proxy. Flask keeps the user's access token in its session and sends it to Nexus;
never put the client secret or access token in Vue.
The browser tab remembers the selected list, sort order, page, and expanded
patient ID in `sessionStorage`, restoring them only after fresh Nexus data loads.
It clears this view state on logout or when the session is no longer authenticated.
Note text, patient records, and unsaved edits are never stored in browser storage.
Without a saved selection, the first allowed citizen list opens automatically.
When creating a note, `Kladde` (Draft) is preselected if Nexus offers that action;
otherwise the user must choose a status. New notes start with the subject
`Afslutning af borger` (Closing a citizen case), which can be edited before saving. CPR in the citizen
list links to the corresponding Nexus citizen page in a new tab; the name is
plain text. The link uses the configured `BASE_URL` and the citizen ID, not the CPR.
Clicking the CPR link also expands that citizen's notes in the list.
For each citizen on the visible page, the list also requests
`GET /api/hcl-depot/orders?patientId=<id>&inProgress=true` through Flask.
The "Igangværende ordrer" (In-progress orders) column shows each order's `requestedDeliveryDate`
as dd/mm/yy (or "Ukendt leveringsdato", Unknown delivery date, when absent), linked to the Nexus
page configured by `NEXUS_ORDER_PAGE_PATH` in a new tab. Orders are not stored in browser
storage. Clicking an order link also expands that citizen's notes
in the list. The app suppresses request logs for Nexus proxy routes and URLs with query
parameters because they can contain patient identifiers or authorization codes;
upstream and ingress logs should likewise avoid retaining sensitive paths and
queries.
For new notes, Vue follows the form prototype's `availablePathwayAssociation`
link and offers active pathways in the `Forløb` (Pathway) selector, including nested
pathways. It initially selects the configured `programPathwayId` if active,
otherwise the active pathway with `programPathwayId` 1, then 2. If none exists,
creation is blocked. Saving assigns the selected pathway as the placement object
and its `patientPathwayId` as `referenceId`; existing notes retain their Nexus
association and cannot change pathways here.
After a create request, the UI only shows a new note if the follow-up Nexus read
finds it. Otherwise it keeps the editor open with a bold red Danish error and
disables another save until the user checks Nexus and cancels, avoiding an
accidental duplicate submission. Successful saves show no message. Unsaved
note text remains only in the current page.
Before a Nexus request, Flask renews an access token nearing expiry using the
refresh token stored in its server-side session. A rotated refresh token replaces
the previous one. If Keycloak rejects renewal or the refresh token is unavailable,
the user must log in again; transient provider failures return an error without
sending the Nexus request. Keycloak's session and refresh-token limits still apply.
Logout uses a 15-second provider-request timeout. If the provider request fails,
the local session remains active and the UI reports an error so logout can be retried.
Use HTTPS for `APP_URL` in production so session cookies are marked Secure;
cookies are HttpOnly and SameSite=Lax. Protect the server-side session store,
which contains refresh tokens.

The default Nexus origin is set by `BASE_URL` and its API prefix by `BASE_PATH`.
Set them in the app environment when targeting a different Nexus installation;
keep `BASE_URL` to the origin, without the API path. `APP_URL` is the separate
public URL used for the login redirect.
Set the following Nexus-specific paths in the server environment (or
`flask/src/.env` for local development) before starting the app:

* `NEXUS_ORDERS_API_PATH`: absolute path to the orders API on `BASE_URL`.
* `NEXUS_FORM_PROTOTYPE_PATH`, `NEXUS_FORM_ACTION_PATH`, and
  `NEXUS_FLAT_REFERENCES_PATH`: paths relative to `BASE_PATH`, each with a
  `{patient_id}` placeholder.
* `NEXUS_CITIZEN_PAGE_PATH` and `NEXUS_ORDER_PAGE_PATH`: absolute page paths
  on `BASE_URL`, each with a `{patient_id}` placeholder.

These settings are required. Flask sends the browser-used paths in the
authenticated, non-cached citizen-list configuration response, so changing
them requires an app restart but not a Vue rebuild. They are not secrets:
authenticated users can inspect them in the browser.

Set `ALLOWED_CITIZEN_LIST_IDS` in the app's runtime environment (for example, on
the Kubernetes pod) to comma-separated numeric preference IDs such as `101,102`.
After login, Vue fetches the IDs from `GET /api/citizen-list-config` and displays
only matching `CITIZEN_LIST` entries. If unset, the default is `5327`;
explicitly setting it to an empty string shows no lists. Restart the pod after
changing its environment; the Vue image does not need rebuilding.
The IDs are sent to the browser, so do not put secrets in this setting. This is
only a UI filter, not access control: Flask still proxies direct requests and
Nexus permissions must restrict access to sensitive data.

For POST and PUT, first GET `/api/csrf` and include its `token` in the
`X-CSRF-Token` header. Send the request body and its `Content-Type`, plus
`If-Match` when updating a resource with an ETag. The proxy preserves Nexus
status codes, response bodies, Content-Type, ETag, and Location. It accepts only
the configured Nexus API prefix, rejects redirects, and limits write bodies to 1 MB.
Nexus responses are not filtered by Flask: limit the client's Nexus permissions
and request only data needed by the UI, especially when it contains personal data.


