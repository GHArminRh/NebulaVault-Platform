"use strict";
const CACHE_NAME = "nebula-vault-shell-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((name) => name.startsWith("nebula-vault-") && name !== CACHE_NAME).map((name) => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET" || request.mode !== "navigate") return;
  event.respondWith(fetch(request).catch(() => new Response(
    '<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b1020"><title>اتصال برقرار نیست</title><body style="margin:0;background:#080d1b;color:#eef3ff;font:16px Tahoma,sans-serif;display:grid;place-items:center;min-height:100vh;text-align:center"><main style="padding:28px"><h1>اتصال اینترنت برقرار نیست</h1><p>برای استفاده از نبیولا والت، اتصال اینترنت را بررسی و دوباره تلاش کنید.</p><a href="/" style="display:inline-block;padding:10px 18px;border-radius:9px;background:#387dff;color:white;font:inherit;text-decoration:none">تلاش دوباره</a></main></body></html>',
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } }
  )));
});
