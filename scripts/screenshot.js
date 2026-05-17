#!/usr/bin/env node
import puppeteer from 'puppeteer';
import { fileURLToPath } from 'url';
import path from 'path';

const args = process.argv.slice(2);

if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
  console.log('Usage: node screenshot.js <url> [output-file] [options]');
  console.log('');
  console.log('Arguments:');
  console.log('  url           The URL to screenshot (required)');
  console.log('  output-file   Output filename (default: screenshot.png)');
  console.log('');
  console.log('Options:');
  console.log('  --fullPage    Capture full page screenshot');
  console.log('  --width=N     Viewport width (default: 1920)');
  console.log('  --height=N    Viewport height (default: 1080)');
  console.log('  --delay=N     Wait N milliseconds before screenshot (default: 0)');
  console.log('');
  console.log('Examples:');
  console.log('  node screenshot.js https://example.com');
  console.log('  node screenshot.js https://example.com output.png --fullPage');
  console.log('  node screenshot.js https://example.com screenshot.png --width=1280 --height=720');
  process.exit(args.length === 0 ? 1 : 0);
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
