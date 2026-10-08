# Vue-Python-Template
Template for vue and python projects.
NB: backend endpoints er åbne udtil (samme som frontend'en). Hvis der skal bruges en "rigtig" backend - deploy [vue](https://github.com/Randers-Kommune-Digitalisering/vue-js-template) og [flask](https://github.com/Randers-Kommune-Digitalisering/python-app-template) i hver sin pod.

## Kørsel af frontend + backend i docker
* Kør ```docker-compose up``` i top dir
* Backend på port 8080, frontend på port 3000

## Kørsel af Frontenden(Vue)
* CD hen til vue folder: ``` cd vue ```
* Installerer afhængigheder: ``` npm install ```
* Compile, hot reload og start frontenden: ``` npm run dev ```

## Kørsel af Bakcenden(Python)
* Start applikationen: ``` python flask/src/main.py ```

## Udviklings commands:
* Bygge docker image: ```docker build -t vue-python-template .```
* Kør container ud fra det image man byggede: ```docker run -p 8080:8080 vue-python-template```
* Lint: ```flake8 python/src tests --count --select=E9,F63,F7,F82 --show-source --statistics```
* Unit tests: ``` pytest ```

## Nexus API from Vue

After login, Vue calls Flask on the same origin. `GET /api/home-ressource` fetches the
Nexus home resource. Other HAL links under
`https://randers.nexus.kmd.dk/api/core/mobile/randers/v2/` can be requested through
`/api/nexus/<path>` with GET, POST, or PUT. Resolve relative links against the Nexus
URL of the response that supplied them, then send the path and query to the local
proxy. Flask keeps the user's access token in its session and sends it to Nexus;
never put the client secret or access token in Vue.

The default Nexus origin is set by `BASE_URL` and its API prefix by `BASE_PATH`.
Set them in the app environment when targeting a different Nexus installation;
keep `BASE_URL` to the origin, without the API path. `APP_URL` is the separate
public URL used for the login redirect.

For POST and PUT, first GET `/api/csrf` and include its `token` in the
`X-CSRF-Token` header. Send the request body and its `Content-Type`, plus
`If-Match` when updating a resource with an ETag. The proxy preserves Nexus
status codes, response bodies, Content-Type, ETag, and Location. It accepts only
the configured Nexus API prefix, rejects redirects, and limits write bodies to 1 MB.
The proxy does not filter Nexus responses: limit the client's Nexus permissions
and request only data needed by the UI, especially when it contains personal data.


