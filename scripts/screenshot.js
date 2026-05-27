#!/usr/bin/env node
import puppeteer from 'puppeteer';
import { fileURLToPath } from 'url';
import path from 'path';

const args = process.argv.slice(2);

if (args.length === 0) {
  console.error('Usage: node screenshot.js <url> [output-file] [--fullPage] [--width=N] [--height=N] [--delay=N]');
  process.exit(1);
}

const url = args[0];
let outputFile = 'screenshot.png';
let fullPage = false;
let width = 1920;
let height = 1080;
let delay = 0;

for (let i = 1; i < args.length; i++) {
  const arg = args[i];
  if (arg.startsWith('--')) {
    if (arg === '--fullPage') {
      fullPage = true;
    } else if (arg.startsWith('--width=')) {
      width = parseInt(arg.split('=')[1]);
    } else if (arg.startsWith('--height=')) {
      height = parseInt(arg.split('=')[1]);
    } else if (arg.startsWith('--delay=')) {
      delay = parseInt(arg.split('=')[1]);
    }
  } else if (!arg.startsWith('-')) {
    outputFile = arg;
  }
}

console.log(`Taking screenshot of: ${url}`);
console.log(`  Output: ${outputFile}`);
console.log(`  Viewport: ${width}x${height}${fullPage ? ', full page' : ''}${delay ? `, delay ${delay}ms` : ''}`);
console.log();

try {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  const page = await browser.newPage();

  await page.setViewport({
    width: width,
    height: height,
    deviceScaleFactor: 1,
  });

  await page.goto(url, {
    waitUntil: 'networkidle2',
    timeout: 30000
  });

  if (delay > 0) {
    await new Promise(resolve => setTimeout(resolve, delay));
  }

  await page.screenshot({
    path: outputFile,
    fullPage: fullPage
  });

  await browser.close();

  console.log(`  [ok] Saved: ${outputFile}`);
} catch (error) {
  console.error(`  [x] Failed: ${error.message}`);
  process.exit(1);
}
