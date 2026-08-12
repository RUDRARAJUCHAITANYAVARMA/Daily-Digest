const ALLOWED_ORIGIN = "https://dailydigest.in";
const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$/;
const PENDING_SUBSCRIPTION_TTL = 24 * 60 * 60;

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}

function htmlPage(heading, message, status = 200) {
  const font = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif";
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Digest</title>
</head>
<body style="margin:0;padding:0;background:#f4f2ec;font-family:${font};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:48px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:440px;background:#ffffff;border-radius:12px;padding:40px 32px;text-align:center;">
          <tr><td style="font-size:13px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#3F9A5C;padding-bottom:20px;">Daily Digest</td></tr>
          <tr><td style="font-size:19px;font-weight:700;color:#1e2b23;padding-bottom:12px;">${heading}</td></tr>
          <tr><td style="font-size:15px;line-height:1.6;color:#3f473f;padding-bottom:24px;">${message}</td></tr>
          <tr><td><a href="https://dailydigest.in" style="color:#3F9A5C;font-size:13px;text-decoration:none;font-weight:600;">dailydigest.in</a></td></tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
  return new Response(html, {
    status,
    headers: { "Content-Type": "text/html; charset=UTF-8", ...corsHeaders() },
  });
}

async function resendFetch(env, path, options = {}) {
  return fetch(`https://api.resend.com${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
}

async function getSubscriberCount(env) {
  const res = await resendFetch(env, `/audiences/${env.RESEND_AUDIENCE_ID}/contacts`);
  if (!res.ok) return 0;
  const data = await res.json();
  const contacts = data.data || [];
  return contacts.filter((c) => !c.unsubscribed).length;
}

function welcomeEmailPayload(email) {
  const text =
    "Hey,\n\n" +
    "This is Chaitanya from Daily Digest. I'm really grateful you subscribed, and I'll make it worth your time every morning.\n\n" +
    "You'll get the ten stories that actually matter, each in three sentences. No ads, no tracking, nothing engineered to keep you scrolling. Two minutes and you're caught up.\n\n" +
    "Your first one lands tomorrow.\n\n" +
    "And if you hit reply and tell me what you're hoping to get out of this, I read every one.\n\n" +
    "See you tomorrow morning,\n" +
    "Chaitanya\n" +
    "dailydigest.in";

  const html = text
    .split("\n\n")
    .map(
      (para) =>
        `<p style="margin:0 0 16px 0; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; font-size:15px; line-height:1.6; color:#1e2b23;">${para.replace(/\n/g, "<br>")}</p>`
    )
    .join("");

  return {
    from: "Daily Digest <newsletter@dailydigest.in>",
    to: email,
    subject: "Thanks for subscribing - your first Digest arrives tomorrow",
    text,
    html,
  };
}

async function sendWelcomeEmail(env, email) {
  const res = await resendFetch(env, "/emails", {
    method: "POST",
    body: JSON.stringify(welcomeEmailPayload(email)),
  });
  if (!res.ok) console.error("Welcome email failed:", await res.text());
  return res.ok;
}

function confirmationEmailPayload(email, confirmationUrl) {
  const text =
    "Hey,\n\n" +
    "Thank you for subscribing to Daily Digest. You're one step away from getting your first Daily Digest tomorrow — just confirm your subscription using the link: " +
    confirmationUrl +
    "\n\nThis link will expire in 24 hours. If you did not request this subscription, no action is needed.\n\n" +
    "Regards,\n" +
    "Daily Digest\n" +
    "dailydigest.in";

  const font = "-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif";
  const html = `
    <p style="margin:0 0 16px 0;font-family:${font};font-size:15px;line-height:1.6;color:#1e2b23;">Hey,</p>
    <p style="margin:0 0 24px 0;font-family:${font};font-size:15px;line-height:1.6;color:#1e2b23;">Thank you for subscribing to Daily Digest. You're one step away from getting your first Daily Digest tomorrow — just confirm your subscription using the link: <a href="${confirmationUrl}" style="color:#3F9A5C;font-weight:700;text-decoration:underline;">Confirm my subscription</a>.</p>
    <p style="margin:0 0 24px 0;font-family:${font};font-size:13px;color:#68736c;">This link will expire in 24 hours. If you did not request this subscription, no action is needed.</p>
    <p style="margin:0;font-family:${font};font-size:15px;line-height:1.6;color:#1e2b23;">Regards,<br>Daily Digest<br>dailydigest.in</p>
  `;

  return {
    from: "Daily Digest <newsletter@dailydigest.in>",
    to: email,
    subject: "Confirm your Daily Digest subscription",
    text,
    html,
  };
}

async function sendConfirmationEmail(env, email, confirmationUrl) {
  const res = await resendFetch(env, "/emails", {
    method: "POST",
    body: JSON.stringify(confirmationEmailPayload(email, confirmationUrl)),
  });
  if (!res.ok) console.error("Confirmation email failed:", await res.text());
  return res.ok;
}

function randomToken() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function tokenKey(token) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(token));
  return `pending:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

async function unsubscribeToken(env, email) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(env.UNSUBSCRIBE_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(email));
  return Array.from(new Uint8Array(signature), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

async function getContact(env, email) {
  const res = await resendFetch(
    env,
    `/audiences/${env.RESEND_AUDIENCE_ID}/contacts/${encodeURIComponent(email)}`
  );
  if (res.status === 404) return { contact: null };
  if (!res.ok) return { error: true };
  return { contact: await res.json() };
}

async function handleSubscribe(request, env) {
  let payload;
  try {
    payload = JSON.parse(await request.text());
  } catch {
    return json({ success: false, message: "Invalid request body." }, 400);
  }

  const email = (payload.email || "").trim().toLowerCase();
  if (!email || !EMAIL_REGEX.test(email)) {
    return json({ success: false, message: "Invalid email address." }, 400);
  }

  const lookup = await getContact(env, email);
  if (lookup.error) {
    return json({ success: false, message: "Something went wrong. Please try again." }, 502);
  }

  if (lookup.contact) {
    const contact = lookup.contact;
    if (!contact.unsubscribed) {
      return json({ success: false, message: "This email is already subscribed." });
    }
  }

  const token = randomToken();
  const key = await tokenKey(token);
  const expiresAt = Date.now() + PENDING_SUBSCRIPTION_TTL * 1000;
  try {
    await env.PENDING_SUBSCRIPTIONS.put(key, JSON.stringify({ email, expiresAt }), {
      expirationTtl: PENDING_SUBSCRIPTION_TTL,
    });
  } catch (error) {
    console.error("Pending subscription storage failed:", error);
    return json({ success: false, message: "Something went wrong. Please try again." }, 502);
  }

  const baseUrl = (env.CONFIRMATION_BASE_URL || new URL(request.url).origin).replace(/\/$/, "");
  const confirmationUrl = `${baseUrl}/confirm?token=${token}`;
  if (!(await sendConfirmationEmail(env, email, confirmationUrl))) {
    await env.PENDING_SUBSCRIPTIONS.delete(key);
    return json({ success: false, message: "We could not send the confirmation email. Please try again." }, 502);
  }

  return json({ success: true, message: "Check your inbox to confirm your subscription." });
}

async function handleConfirmation(request, env) {
  const token = new URL(request.url).searchParams.get("token");
  if (!token || !/^[a-f0-9]{64}$/.test(token)) {
    return htmlPage("Link expired", "This confirmation link is invalid or has expired. Please subscribe again to get a new one.", 400);
  }

  const key = await tokenKey(token);
  const pending = await env.PENDING_SUBSCRIPTIONS.get(key, "json");
  if (!pending || pending.expiresAt < Date.now()) {
    return htmlPage("Link expired", "This confirmation link is invalid or has expired. Please subscribe again to get a new one.", 400);
  }

  const lookup = await getContact(env, pending.email);
  if (lookup.error) {
    return htmlPage("Something went wrong", "We could not confirm your subscription. Please try again later.", 502);
  }

  let contactResponse;
  if (!lookup.contact) {
    contactResponse = await resendFetch(env, `/audiences/${env.RESEND_AUDIENCE_ID}/contacts`, {
      method: "POST",
      body: JSON.stringify({ email: pending.email, unsubscribed: false }),
    });
  } else if (lookup.contact.unsubscribed) {
    contactResponse = await resendFetch(
      env,
      `/audiences/${env.RESEND_AUDIENCE_ID}/contacts/${encodeURIComponent(pending.email)}`,
      { method: "PATCH", body: JSON.stringify({ unsubscribed: false }) }
    );
  } else {
    contactResponse = new Response(null, { status: 200 });
  }

  if (!contactResponse.ok) {
    console.error("Contact confirmation failed:", contactResponse.status, await contactResponse.text());
    return htmlPage("Something went wrong", "We could not confirm your subscription. Please try again later.", 502);
  }

  await env.PENDING_SUBSCRIPTIONS.delete(key);
  if (!(await sendWelcomeEmail(env, pending.email))) {
    return htmlPage("You're subscribed", "Your subscription is confirmed, but the welcome email could not be sent.", 502);
  }

  return htmlPage("You're subscribed!", "Your first Daily Digest arrives tomorrow morning.");
}

async function handleUnsubscribe(request, env) {
  const url = new URL(request.url);
  const email = (url.searchParams.get("email") || "").trim().toLowerCase();
  const token = url.searchParams.get("token") || "";

  if (!email || !EMAIL_REGEX.test(email) || !token) {
    return htmlPage("Invalid link", "This unsubscribe link is invalid.", 400);
  }

  const expectedToken = await unsubscribeToken(env, email);
  if (!timingSafeEqual(token, expectedToken)) {
    return htmlPage("Invalid link", "This unsubscribe link is invalid.", 400);
  }

  const lookup = await getContact(env, email);
  if (lookup.error) {
    return htmlPage("Something went wrong", "We could not process your request. Please try again later.", 502);
  }

  if (lookup.contact && !lookup.contact.unsubscribed) {
    const res = await resendFetch(
      env,
      `/audiences/${env.RESEND_AUDIENCE_ID}/contacts/${encodeURIComponent(email)}`,
      { method: "PATCH", body: JSON.stringify({ unsubscribed: true }) }
    );
    if (!res.ok) {
      console.error("Unsubscribe failed:", res.status, await res.text());
      return htmlPage("Something went wrong", "We could not process your request. Please try again later.", 502);
    }
  }

  return htmlPage("Unsubscribed", "You've been unsubscribed from Daily Digest. Sorry to see you go.");
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    if (request.method === "GET") {
      const url = new URL(request.url);
      if (url.pathname === "/unsubscribe") {
        return handleUnsubscribe(request, env);
      }
      if (url.searchParams.has("token")) {
        return handleConfirmation(request, env);
      }
      const count = await getSubscriberCount(env);
      return json({ success: true, count });
    }

    if (request.method === "POST") {
      return handleSubscribe(request, env);
    }

    return json({ success: false, message: "Method not allowed." }, 405);
  },
};
