#!/usr/bin/env node
import puppeteer from "puppeteer";

const [url, ...rest] = process.argv.slice(2);

if (!url) {
    console.error("Usage: node screenshot.js <url> [output-file] [--fullPage] [--width=N] [--height=N] [--delay=N]");
    process.exit(1);
}

const flags = Object.fromEntries(rest.filter((a) => a.startsWith("--")).map((a) => a.slice(2).split("=")));
const outputFile = rest.find((a) => !a.startsWith("-")) ?? "screenshot.png";
const width = parseInt(flags.width ?? 1920);
const height = parseInt(flags.height ?? 1080);
const delay = parseInt(flags.delay ?? 0);
const fullPage = "fullPage" in flags;

console.log(`Taking screenshot of: ${url}`);
console.log(`  Output: ${outputFile}, viewport: ${width}x${height}${fullPage ? ", full page" : ""}${delay ? `, delay ${delay}ms` : ""}\n`);

const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"] });
const page = await browser.newPage();
await page.setViewport({ width, height });
await page.goto(url, { waitUntil: "networkidle2", timeout: 30000 });
if (delay > 0) await new Promise((r) => setTimeout(r, delay));
await page.screenshot({ path: outputFile, fullPage });
await browser.close();

console.log(`  [ok] Saved: ${outputFile}`);
