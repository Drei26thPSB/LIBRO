Render deployment — quick steps

1) Push this repository to GitHub (if not already).
2) Create a free account on https://render.com and choose "New -> Web Service".
3) Connect your GitHub repo and select the branch to deploy.
4) Set the `Start Command` to:
   `gunicorn Server:app --bind 0.0.0.0:$PORT`
5) Set environment variables under the Render service settings:
   - `LIBRO_USER` and `LIBRO_PASS` to enable Basic Auth in the app
   - (optional) `LIBRO_PORT` if you want a custom port
6) Deploy — Render will build from `requirements.txt`.

Notes
- The app uses HTTP Basic Auth when `LIBRO_USER` and `LIBRO_PASS` are set (recommended).
- For an "unlisted" but protected site: keep `LIBRO_USER`/`LIBRO_PASS` set and don't share the URL publicly.
- I can add a GitHub Action or a `render.yaml` for fully-automatic infra if you want.
