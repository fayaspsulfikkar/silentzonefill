# Android Tasker + AutoNotification Setup Guide

## Overview

This guide configures your Android phone to:
1. Listen for WhatsApp notifications from the registration announcement.
2. Extract any Google Forms URL from the notification text.
3. Forward the data to the cloud server via HTTPS POST.

---

## Prerequisites

- **Tasker** (paid, Google Play Store)
- **AutoNotification** plugin for Tasker (paid, by João Dias)
- Both apps whitelisted from battery optimization
- Your cloud server URL and webhook secret token

---

## Step 1: Disable Battery Optimization

Go to **Settings → Battery → Battery Optimization**.

Find **Tasker** and **AutoNotification** → set both to **Don't Optimize** (or **Unrestricted**).

> ⚠️ This is critical. Without it, Android Doze mode may kill the notification listener — causing the bot to miss the announcement entirely.

---

## Step 2: Grant Notification Access

Go to **Settings → Apps → Special App Access → Notification Access**.

Enable **AutoNotification**.

---

## Step 3: Create the Tasker Profile

### Profile Trigger: AutoNotification Intercept

1. Open Tasker → **+** → **Profile** → **Event**
2. Select **Plugin** → **AutoNotification** → **Intercept**
3. Configure:
   - **Application:** WhatsApp
   - **Text Contains:** `forms.gle|docs.google.com/forms`

### Linked Task: Forward to Server

Create a new task and add these actions in order:

---

#### Action 1 — Extract Google Forms URL

Use **JavaScriptlet** to extract the URL client-side (handles truncated notifications):

```javascript
var text = global('an_text');
var match = text.match(
  /https?:\/\/(?:docs\.google\.com\/forms\/d\/e\/[\w-]+\/viewform[\w?=&]*|forms\.gle\/[\w-]+)/i
);
setGlobal('form_url', match ? match[0] : '');
```

---

#### Action 2 — HTTP POST to Server

Add action: **Net** → **HTTP Request**

```
Method:  POST
URL:     https://YOUR_SERVER_DOMAIN/api/registration/announcement
Headers:
  Content-Type: application/json
  X-Webhook-Secret: YOUR_WEBHOOK_SECRET
Body:
{
  "app_package": "%an_package",
  "group_name":  "%an_title",
  "message_text": "%an_text",
  "form_url": "%form_url",
  "timestamp": "%TIMES"
}
Timeout: 15
```

Replace `YOUR_SERVER_DOMAIN` and `YOUR_WEBHOOK_SECRET` with real values.

> ⚠️ Store the webhook secret inside Tasker only. Never write it in a file you sync to cloud.

---

#### Action 3 (Optional) — Local Confirmation Notification

Add action: **Alert** → **Notify**

```
Title: Silent Zone Bot
Text:  Announcement forwarded ✓
```

---

## Step 4: Test the Setup

1. Temporarily widen the trigger filter to match any WhatsApp message.
2. Send yourself a test WhatsApp message containing a valid Google Forms URL.
3. Verify the Tasker task fires.
4. Check server logs: you should see `HTTP 202 Accepted`.
5. Check the dashboard for the received attempt.
6. Restore the original filter.

---

## Manufacturer-Specific Battery Whitelist Steps

| Manufacturer | Path |
|---|---|
| **Samsung One UI** | Settings → Device Care → Battery → Background Usage Limits → remove Tasker from sleeping apps |
| **Xiaomi MIUI** | Settings → Apps → Manage Apps → Tasker → Battery Saver → No Restrictions. Also enable Autostart. |
| **OnePlus OxygenOS** | Settings → Battery → Battery Optimization → All Apps → Tasker/AutoNotification → Don't Optimize |
| **Huawei EMUI** | Phone Manager → App Launch → Tasker → manage manually → enable all three toggles |

---

## Known Limitations

| Issue | Impact | Mitigation |
|---|---|---|
| Android Doze mode | Tasker delayed or killed | Battery whitelist (see above) |
| WhatsApp notification preview disabled | Tasker sees no message text | Enable message previews in WhatsApp settings |
| Notification truncation on Android | Long URL cut off | URL is extracted client-side via JavaScriptlet |
| WhatsApp message arrives when screen is locked | Usually still works | Test this explicitly in Step 4 |

---

## Fallback: Manual Dashboard Submission

If Tasker fails, open the web dashboard in any browser:

```
https://YOUR_SERVER_DOMAIN/
```

Paste the Google Forms URL in the **Manual Submission** field and click **Start Registration**.

The automation proceeds identically to the automatic path.

