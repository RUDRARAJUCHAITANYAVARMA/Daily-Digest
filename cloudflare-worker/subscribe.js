const ALLOWED_ORIGIN = "https://dailydigest.in";
const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$/;

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
    "This is Chaitanya, the person who builds Daily Digest. I just wanted to say thank you for subscribing.\n\n" +
    "You'll get the ten most important stories in the world every morning, each one in three sentences. No ads, no tracking, nothing trying to keep you scrolling. A couple of minutes and you're done.\n\n" +
    "Thank you again for trusting me with a spot in your inbox. I know that's not a small thing to give away, and I'm grateful you did.\n\n" +
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
    subject: "📰 Welcome to Daily Digest",
    text,
    html,
  };
}

async function sendWelcomeEmail(env, email) {
  const res = await resendFetch(env, "/emails", {
    method: "POST",
    body: JSON.stringify(welcomeEmailPayload(email)),
  });
  if (!res.ok) {
    console.error("Welcome email failed:", await res.text());
  }
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

  const existing = await resendFetch(
    env,
    `/audiences/${env.RESEND_AUDIENCE_ID}/contacts/${encodeURIComponent(email)}`
  );

  if (existing.status === 200) {
    const contact = await existing.json();
    if (!contact.unsubscribed) {
      return json({ success: false, message: "This email is already subscribed." });
    }
    const patch = await resendFetch(
      env,
      `/audiences/${env.RESEND_AUDIENCE_ID}/contacts/${encodeURIComponent(email)}`,
      { method: "PATCH", body: JSON.stringify({ unsubscribed: false }) }
    );
    if (!patch.ok) {
      return json({ success: false, message: "Something went wrong. Please try again." }, 502);
    }
    await sendWelcomeEmail(env, email);
    return json({ success: true, message: "Successfully subscribed." });
  }

  const create = await resendFetch(env, `/audiences/${env.RESEND_AUDIENCE_ID}/contacts`, {
    method: "POST",
    body: JSON.stringify({ email, unsubscribed: false }),
  });

  if (!create.ok) {
    return json({ success: false, message: "Something went wrong. Please try again." }, 502);
  }

  await sendWelcomeEmail(env, email);
  return json({ success: true, message: "Successfully subscribed." });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    if (request.method === "GET") {
      const count = await getSubscriberCount(env);
      return json({ success: true, count });
    }

    if (request.method === "POST") {
      return handleSubscribe(request, env);
    }

    return json({ success: false, message: "Method not allowed." }, 405);
  },
};
