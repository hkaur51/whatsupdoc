# Deploy DentBot (WhatsUpDoc) to Render

This backend runs as a **Web Service** on Render. Calendar is stored in the database only (no Google Calendar); patients and doctors can add appointments to their **phone calendar** via the ICS link sent in WhatsApp.

---

## 1. Prepare the repo

- Ensure the **backend** runs from the `backend` directory (where `server.py` and `requirements.txt` live).
- Commit and push your code to GitHub (or connect the repo Render will use).

---

## 2. Create a MongoDB database

- Use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (free tier is enough).
- Create a cluster and a database (e.g. `whatsup_doc`).
- Create a user and get the **connection string** (e.g. `mongodb+srv://user:pass@cluster.mongodb.net/whatsup_doc?retryWrites=true&w=majority`).
- Add your Render service IP to Atlas IP Access List, or allow access from anywhere (`0.0.0.0/0`) for simplicity.

---

## 3. Create a Web Service on Render

1. **Dashboard** → **New** → **Web Service**.
2. Connect your GitHub repo.
3. Configure:
   - **Name:** e.g. `dentbot` or `whatsupdoc`.
   - **Region:** Choose one (e.g. Singapore for India).
   - **Branch:** `main` (or your default).
   - **Root Directory:** Leave empty if the repo root contains the app, or set to the folder that contains `server.py` (e.g. `backend` if the repo root is the project root).
   - **Runtime:** Python 3.
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
     If your app is in `backend/`:
     ```bash
     cd backend && pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn server:app --host 0.0.0.0 --port $PORT
     ```
     If your app is in `backend/`:
     ```bash
     cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
     ```
     Render sets `PORT`; use it so the service listens on the correct port.

---

## 4. Environment variables (Render)

In the Render Web Service → **Environment** tab, add:

| Key | Value | Notes |
|-----|--------|--------|
| `MONGO_URL` | `mongodb+srv://...` | Your Atlas connection string |
| `DB_NAME` | `whatsup_doc` | Database name |
| `CORS_ORIGINS` | `*` or your frontend URL | Comma-separated if multiple |
| `WHATSAPP_VERIFY_TOKEN` | A secret string | Same as in Meta Developer app (webhook verify) |
| `WHATSAPP_API_TOKEN` | Your WhatsApp Cloud API token | Long-lived access token |
| `WHATSAPP_PHONE_NUMBER_ID` | Phone number ID | From Meta Developer app |
| `WHATSAPP_MOCK_MODE` | `false` | Set to `false` for real WhatsApp |
| `BASE_URL` | `https://your-service-name.onrender.com` | Your Render URL (no trailing slash); used for calendar.ics links |

Optional (if you use them):

- `EMERGENT_LLM_KEY` – only if you add an LLM provider later.

After saving, Render will redeploy.

---

## 5. WhatsApp Cloud API webhook

1. In [Meta for Developers](https://developers.facebook.com/), open your app → **WhatsApp** → **Configuration**.
2. Under **Webhook**, set:
   - **Callback URL:** `https://your-service-name.onrender.com/api/webhook/whatsapp`
   - **Verify Token:** Same as `WHATSAPP_VERIFY_TOKEN` in Render.
3. Subscribe to **messages** (and any other events you need).
4. When Meta sends a GET request to the callback URL with `hub.mode=subscribe` and `hub.verify_token=...`, your app must return `hub.challenge` (your webhook already does this).

---

## 6. After deploy

- **Health check:**  
  `GET https://your-service-name.onrender.com/api/health`
- **Root:**  
  `GET https://your-service-name.onrender.com/api`
- **Calendar link for a patient:**  
  After an appointment is created, the backend can send (when `BASE_URL` is set):  
  `https://your-service-name.onrender.com/api/appointments/{appointment_id}/calendar.ics`  
  Opening this on a phone lets the user add the event to their device calendar.

---

## 7. First-time setup (clinic + doctor)

Run the setup script **once** locally (with the same `MONGO_URL` and `DB_NAME` as production) to create the clinic and doctor:

```bash
cd backend
pip install -r requirements.txt
# Set MONGO_URL and DB_NAME in .env or export them
python setup_clinic.py
```

Or use your existing API to create clinic/doctor if you have admin endpoints.

---

## 8. Free tier and cold starts

- On the free tier, the service may spin down after inactivity; the first request after that can be slow (cold start).
- For production, consider the paid tier so the service stays up and WhatsApp webhooks get faster responses.

---

## Summary checklist

- [ ] MongoDB Atlas cluster and connection string
- [ ] Render Web Service with correct **Root Directory**, **Build** and **Start** commands
- [ ] All env vars set (especially `MONGO_URL`, `WHATSAPP_*`, `BASE_URL`)
- [ ] Webhook URL and Verify Token set in Meta Developer app
- [ ] `BASE_URL` set to your Render URL for phone calendar links
- [ ] Run `setup_clinic.py` (or create clinic/doctor via API) so the bot has an active clinic and doctor
