# Free Android Setup Guide — MacroDroid (100% Free Alternative to Tasker)

If you don't own Tasker, **MacroDroid** is completely free on the Google Play Store (free tier includes 5 macros — you only need 1).

---

## Step 1: Install MacroDroid (Free)
1. Open Google Play Store on your Android phone.
2. Search for **MacroDroid - Device Automation** (by ArloSoft) and install it.

---

## Step 2: Grant Permissions & Disable Battery Optimization
1. Open MacroDroid.
2. Grant **Notification Access** when prompted (Settings ➔ Apps ➔ Special App Access ➔ Notification Access ➔ Enable MacroDroid).
3. Whitelist MacroDroid from Battery Optimization:
   - Go to phone **Settings ➔ Battery ➔ Battery Optimization**.
   - Set MacroDroid to **Don't Optimize** (or **Unrestricted**).
   *(This prevents Android from killing it when your screen is locked).*

---

## Step 3: Create the Silent Zone Forwarding Macro

1. In MacroDroid, tap **Add Macro** (top left).
2. Name the macro: `Silent Zone Forwarder`.

### 1. Add Trigger (Red "+")
- Tap **+** on the Triggers section.
- Select **Device Events** ➔ **Notification** ➔ **Notification Received**.
- Choose **Select Application(s)** ➔ check **WhatsApp** ➔ tap OK.
- Under **Text Content**, select **Matches (wildcard/regex)**:
  - Enter: `*forms.gle*` OR `*docs.google.com/forms*`
  - *(Or leave as "Any Content" if you want it to trigger on any WhatsApp notification).*
- Tap **OK**.

### 2. Add Action (Blue "+")
- Tap **+** on the Actions section.
- Select **Connectivity** ➔ **HTTP Request**.
- Configure the request:
  - **Request Method:** `POST`
  - **URL:** `https://YOUR_TUNNEL_OR_VPS_DOMAIN/api/registration/announcement`
  - **Content Type:** `application/json`
  - **Request Headers (Custom Headers):**
    - Tap **+ Add Header**:
      - Name: `X-Webhook-Secret`
      - Value: `00733e2b704947118d76d8b5fd212e9fe2168ab4f1c1ccee`
  - **Request Body (Text / Raw Content):**
    Paste this exact JSON payload:
    ```json
    {
      "app_package": "com.whatsapp",
      "group_name": "{not_title}",
      "message_text": "{notification}",
      "timestamp": "{system_time}"
    }
    ```
    *(MacroDroid automatically replaces `{not_title}` with the group name and `{notification}` with the message body!)*
  - Tap **OK** / Save.

### 3. Add Confirmation Alert (Optional, Blue "+")
- Tap **+** on Actions ➔ **Notification** ➔ **Display Notification**.
  - Title: `Silent Zone Bot`
  - Message: `Forwarded to server ✓`

### 4. Save Macro
- Tap the **✓ (Save)** icon in the bottom right corner.
- Toggle the macro switch to **ON**.

---

## Step 4: Test from Phone
1. Lock your phone screen.
2. From a friend's phone or secondary account, send a test message to your WhatsApp containing:
   `https://docs.google.com/forms/d/e/1FAIpQLScCaHWLIShewJ_UvawVMaRwEx8uossbaOWn_OrQV6upSn83Sw/viewform`
3. Notice that within ~1 second:
   - MacroDroid intercepts the notification even while locked.
   - It sends the HTTPS POST to your server.
   - The server automates the form submission.
   - The web dashboard updates to `SUBMITTED`.

