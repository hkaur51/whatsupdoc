# Using your own WhatsApp Business number with WhatsUpDoc

This guide explains how to **purchase or register a WhatsApp Business number** and connect it to WhatsUpDoc so doctors and patients can use it on WhatsApp.

---

## Option A: Meta WhatsApp Cloud API (direct)

You use a phone number (new or existing), register it as WhatsApp Business, and get API access from Meta.

### 1. Get a phone number

- **New number:** Buy a SIM (or use a virtual number provider that supports WhatsApp Business API). The number must be able to receive SMS or voice calls for verification.
- **Existing number:** You can use your clinic’s existing business number if it is not already on WhatsApp (or you’re okay moving it to the API). Once you register it with the API, the regular WhatsApp app can’t use it on the same number.

### 2. Create a Meta Business and app

1. Go to [Meta for Developers](https://developers.facebook.com/) and sign in.
2. Create a **Meta Business Account** if you don’t have one (required for WhatsApp Business API).
3. Create an **App** → choose **Business** type.
4. Add the **WhatsApp** product to the app.

### 3. Register your phone number and get credentials

1. In the app dashboard: **WhatsApp** → **API Setup** (or **Getting Started**).
2. Add your **phone number** (with country code). Meta will send a verification code by SMS or voice; enter it to verify.
3. After verification you get:
   - **Phone number ID** – a long numeric ID for this number (use this as `WHATSAPP_PHONE_NUMBER_ID`).
   - **WhatsApp Business Account ID** – for the business account.
4. Create a **permanent access token**:
   - **WhatsApp** → **API Setup** → **Temporary access token** has a “Generate” option; for production use a **System User** token that doesn’t expire.
   - In **Business Settings** → **Users** → **System Users** → create a system user, assign it to your app, and generate a token with `whatsapp_business_messaging` and `whatsapp_business_management`. Use this token as `WHATSAPP_API_TOKEN`.

### 4. Configure the webhook in your app

1. In the app: **WhatsApp** → **Configuration**.
2. Under **Webhook**:
   - **Callback URL:** `https://YOUR-RENDER-URL/api/webhook/whatsapp`  
     (e.g. `https://whatsupdoc.onrender.com/api/webhook/whatsapp`)
   - **Verify token:** Any secret string you choose (e.g. a long random string). Set the **same** value in your server as `WHATSAPP_VERIFY_TOKEN`.
3. Click **Verify and Save**.
4. Subscribe to **messages** (and optionally **message_deliveries**, **message_reads**).

### 5. Set environment variables on Render

In your Render service → **Environment**, set:

| Variable | Value |
|----------|--------|
| `WHATSAPP_MOCK_MODE` | `false` |
| `WHATSAPP_API_TOKEN` | Your permanent Meta access token |
| `WHATSAPP_PHONE_NUMBER_ID` | The Phone number ID from step 3 |
| `WHATSAPP_VERIFY_TOKEN` | Same verify token as in the webhook |

Redeploy the service. Incoming messages will hit your webhook; replies will be sent via the Cloud API from your WhatsApp Business number.

---

## Option B: BSP (Business Solution Provider)

If Meta’s dashboard is not available in your region or you prefer a provider:

- **Twilio** – [Twilio WhatsApp](https://www.twilio.com/whatsapp) (pay per message, they host the number).
- **360dialog** – [360dialog](https://www.360dialog.com/) (popular in Europe/India for WhatsApp API).
- **MessageBird**, **Gupshup**, etc. – Same idea: you get a WhatsApp Business number and API credentials; they forward webhooks to your server.

Steps are similar in idea:

1. Sign up with the BSP and **register or buy a WhatsApp Business number**.
2. In the BSP dashboard, set your **webhook URL** to:  
   `https://YOUR-RENDER-URL/api/webhook/whatsapp`  
   (If the BSP uses a different path or payload, you may need a small adapter in the backend.)
3. Get from the BSP:
   - **Access token** (or API key) → use as `WHATSAPP_API_TOKEN` (or map to whatever your code expects).
   - **Phone number ID** (or equivalent) → use as `WHATSAPP_PHONE_NUMBER_ID`.
4. Set `WHATSAPP_MOCK_MODE=false` and the same env vars on Render.

**Note:** WhatsUpDoc’s webhook and send logic are written for **Meta’s WhatsApp Cloud API** (Option A). If your BSP uses a different API (e.g. Twilio’s own WhatsApp API), the webhook payload and send URL may differ; you’d then either use our **Twilio adapter** (`/twilio-whatsapp`) for receiving and add a Twilio send path in code, or add a thin adapter that translates BSP ↔ Meta format.

---

## Checklist once your number is connected

- [ ] Number verified and **Phone number ID** and **API token** obtained.
- [ ] Webhook URL set to `https://YOUR-RENDER-URL/api/webhook/whatsapp` and verified.
- [ ] `WHATSAPP_VERIFY_TOKEN` matches the value in Meta (or BSP) webhook config.
- [ ] `WHATSAPP_MOCK_MODE=false`, `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` set on Render.
- [ ] Redeploy; send a test message to your WhatsApp Business number and confirm the bot replies.

---

## Cost notes

- **Meta Cloud API:** Conversation-based pricing (business-initiated vs user-initiated). Check [Meta WhatsApp Pricing](https://developers.facebook.com/docs/whatsapp/pricing).
- **BSPs:** Usually per-message or monthly fees; check the provider’s pricing.

Using **your own WhatsApp Business number** means that number is the one doctors and patients see and use for WhatsUpDoc.
