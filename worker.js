// Cloudflare Worker — televideoimage.hasanahmed.workers.dev
// Paste this in the Worker editor and Deploy. No extra settings needed.
// Only edit ORIGIN below to your Render URL after the Render service is live.

const ORIGIN = "https://YOUR-RENDER-APP.onrender.com"; // <-- change this once

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = ORIGIN.replace(/\/$/, "") + url.pathname + url.search;

    const fwdHeaders = new Headers(request.headers);
    // Strip Cloudflare/identity headers so origin can't be guessed from echoes
    [
      "cf-connecting-ip", "cf-ipcountry", "cf-ray", "cf-visitor",
      "cf-worker", "x-forwarded-for", "x-forwarded-host",
      "x-forwarded-proto", "x-real-ip", "host", "referer", "origin"
    ].forEach(h => fwdHeaders.delete(h));

    const init = {
      method: request.method,
      headers: fwdHeaders,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    };

    let upstream;
    try {
      upstream = await fetch(target, init);
    } catch (e) {
      return new Response("Service unavailable", { status: 502 });
    }

    const headers = new Headers(upstream.headers);
    // Hide origin / server fingerprints
    [
      "server", "via", "x-powered-by", "x-render-origin-server",
      "rndr-id", "x-served-by", "x-cache", "x-cache-hits",
      "cf-cache-status", "report-to", "nel"
    ].forEach(h => headers.delete(h));

    // Rewrite any absolute Render URLs in Location header
    const loc = headers.get("location");
    if (loc && loc.startsWith(ORIGIN)) {
      headers.set("location", loc.slice(ORIGIN.length) || "/");
    }

    headers.set("x-frame-options", "SAMEORIGIN");
    headers.set("referrer-policy", "no-referrer");

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers,
    });
  },
};
