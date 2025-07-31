require('dotenv').config();
const puppeteer = require("puppeteer");
const axios = require("axios");
const fs = require("fs");
const dayjs = require("dayjs");
const utc = require("dayjs/plugin/utc");
const timezone = require("dayjs/plugin/timezone");
dayjs.extend(utc);
dayjs.extend(timezone);

// === PROXY SETTINGS ===
const proxy = {
  type: "http",
  ip: "isp.decodo.com",
  port: "10001",
  username: "spg1c4utf1",
  password: "9VUm5exYtkh~iS8h6y"
};

// ------------------- CONFIG -------------------
const MAIN_ACCOUNT = {
  username: "iamvirk05",
  password: "virksaab",
  sessionFile: "iamvirk05.json",
};

const SCRAPING_ACCOUNTS = [
  { username: "kiransharma0580", password: "virksaabji", sessionFile: "kiransharma0580.json" },
  { username: "yuktisharmaaa11", password: "virksaabji", sessionFile: "yuktisharmaaa11.json" },
];

const LOCATION_LINKS = [
  "https://www.instagram.com/cristiano/tagged/",
  "https://www.instagram.com/explore/locations/221659584/ludhiana-punjab-india/recent/",
  "https://www.instagram.com/explore/locations/234739075/amritsar-punjab/recent/",
  "https://www.instagram.com/explore/locations/110684188959162/chandigarh-india/recent/",
  "https://www.instagram.com/explore/locations/252633351/himachal-pradesh/recent/",
  "https://www.instagram.com/explore/locations/215141266/delhi-india/recent/",
  "https://www.instagram.com/explore/locations/216978098/mumbai-maharashtra/recent/",
  "https://www.instagram.com/explore/locations/100131175266024/varanasi-kashi-banaras/recent/",
  "https://www.instagram.com/explore/locations/212948652/jaipur-rajasthan/recent/",
  "https://www.instagram.com/explore/locations/1754540318139359/gurugram/recent/"
];

const OTP_URL = "https://raw.githubusercontent.com/virkx3/igbot/refs/heads/main/otp.txt";
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const REPO = process.env.REPO;
const BRANCH = process.env.BRANCH || "main";
const USERNAMES = "usernames.txt";

// ✅ Confirm that .env loaded correctly
console.log("ENV Loaded:", { GITHUB_TOKEN, REPO, BRANCH });

// ------------------- UTILS -------------------
function delay(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

function randomDelay(min, max) {
  return delay(Math.floor(Math.random() * (max - min + 1) + min));
}

function normalizeInstagramUrl(url) {
  const match = url.match(/instagram\.com\/(?:p|reel)\/([a-zA-Z0-9_-]+)/);
  return match ? `https://www.instagram.com/p/${match[1]}/` : url;
}

function extractUsernameFromUrl(url) {
  const match = url.match(/instagram\.com\/([^/]+)\/(?:p|reel)\//);
  return match ? match[1] : null;
}


async function fetchFromGitHub(file) {
  try {
    const res = await axios.get(
      `https://raw.githubusercontent.com/${REPO}/${BRANCH}/data2/${file}`,
      { headers: { Authorization: `Bearer ${GITHUB_TOKEN}` } }
    );
    console.log(`✅ Fetched ${file}`);
    return res.data;
  } catch (err) {
    console.log(`⚠️ Could not fetch ${file}: ${err.message}`);
    return null;
  }
}

async function uploadToGitHub(remotePath, localPathOrContent) {
  const url = `https://api.github.com/repos/${REPO}/contents/data2/${remotePath}`;
  const headers = { Authorization: `Bearer ${GITHUB_TOKEN}` };

  const content = fs.existsSync(localPathOrContent)
    ? fs.readFileSync(localPathOrContent)
    : Buffer.from(localPathOrContent);

  try {
    const { data } = await axios.get(url, { headers });
    await axios.put(
      url,
      {
        message: `Update ${remotePath}`,
        content: content.toString("base64"),
        sha: data.sha,
        branch: BRANCH,
      },
      { headers }
    );
    console.log(`✅ Uploaded (updated) ${remotePath}`);
  } catch (err) {
    if (err.response?.status === 404) {
      await axios.put(
        url,
        {
          message: `Create ${remotePath}`,
          content: content.toString("base64"),
          branch: BRANCH,
        },
        { headers }
      );
      console.log(`✅ Uploaded (created) ${remotePath}`);
    } else {
      console.log(`❌ Upload failed: ${err.message}`);
    }
  }
}


// ------------------- USERNAME LOGIC -------------------
const usernameBuffer = new Set();

async function addUsernameIfNotExists(username) {
  usernameBuffer.add(username.trim());

  if (usernameBuffer.size >= 40) {
    let local = fs.existsSync(USERNAMES) ? fs.readFileSync(USERNAMES, "utf8") : "";
    const lines = local.split("\n").map(l => l.trim()).filter(Boolean);
    const combined = new Set([...usernameBuffer, ...lines]);
    const updated = Array.from(combined).join("\n") + "\n";

    fs.writeFileSync(USERNAMES, updated);
    await uploadToGitHub(USERNAMES, updated); // ✅ EH LINE MAIN POINT AE
    console.log(`✅ Uploaded batch: ${usernameBuffer.size} usernames`);
    usernameBuffer.clear();
  } else {
    console.log(`✅ Buffered: @${username}`);
  }

  return true;
}



// ------------------- SESSION HANDLING -------------------
async function loadSession(page, sessionFile) {
  const raw = await fetchFromGitHub(sessionFile);
  if (!raw) return false;

  try {
    const cookies = JSON.parse(typeof raw === "string" ? raw : JSON.stringify(raw));
    if (!Array.isArray(cookies) || cookies.length === 0) return false;
    await page.setCookie(...cookies);
    console.log(`🔁 Loaded session: ${sessionFile}`);
    return true;
  } catch {
    return false;
  }
}

async function saveSession(page, sessionFile) {
  const cookies = await page.cookies();
  const valid = cookies.find((c) => c.name === "sessionid");
  if (valid) {
    fs.writeFileSync(sessionFile, JSON.stringify(cookies, null, 2));
    console.log(`✅ Saved local: ${sessionFile}`);
    await uploadToGitHub(sessionFile, sessionFile);
    console.log(`✅ Uploaded remote: ${sessionFile}`);
    return true;
  }
  console.log(`❌ No sessionid — not saved`);
  return false;
}

// ------------------- LOGIN + OTP -------------------
async function fetchOTP() {
  try {
    const res = await axios.get(OTP_URL);
    const otp = res.data.trim();
    return otp.length >= 4 && otp.length <= 8 ? otp : null;
  } catch {
    return null;
  }
}

async function login(page, account) {
  console.log(`🔐 Logging in: @${account.username}`);
  await page.goto("https://www.instagram.com/accounts/login/", { waitUntil: "networkidle2" });
  await page.waitForSelector('input[name="username"]', { timeout: 15000 });
  await page.type('input[name="username"]', account.username, { delay: 100 });
  await page.type('input[name="password"]', account.password, { delay: 100 });
  await page.click('button[type="submit"]');
  await delay(8000);

  const otpInput = await page.$('input[name="verificationCode"]');
  if (otpInput) {
    console.log(`🔐 Waiting OTP...`);
    await delay(60000);
    for (let i = 0; i < 60; i++) {
      const otp = await fetchOTP();
      if (otp) {
        console.log(`📩 OTP: ${otp}`);
        await page.type('input[name="verificationCode"]', otp, { delay: 100 });
        await page.click("button[type=button]");
        break;
      }
      await delay(1000);
    }
  }

  await page.waitForNavigation({ waitUntil: "networkidle2", timeout: 15000 }).catch(() => {});
  console.log(`✅ Logged in: @${account.username}`);
  await saveSession(page, account.sessionFile);
}

// ------------------- SCRAPE & WATCH (Location-Based) -------------------
async function scrapeUsernames(page, unusedTarget = "", maxUsernames = 50) {
  const locationUrl = LOCATION_LINKS[Math.floor(Math.random() * LOCATION_LINKS.length)];
  console.log(`📍 Scraping from location: ${locationUrl}`);
  await page.goto(locationUrl, { waitUntil: "networkidle2" });

  // ✅ 3 Scrolls
  for (let i = 0; i < 3; i++) {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await delay(2000 + Math.random() * 2000); // 2–4 sec wait
  }

  // ✅ Grab post/reel links
  const links = await page.$$eval(
    "a[href*='/p/'], a[href*='/reel/']",
    as => as.map(a => a.href)
  );

  const uniqueLinks = [...new Set(links)];
  uniqueLinks.sort(() => Math.random() - 0.5);

  const usernames = new Set();

  for (const link of uniqueLinks) {
    if (usernames.size >= maxUsernames) break;

    const cleanUrl = normalizeInstagramUrl(link);
    const username = extractUsernameFromUrl(cleanUrl);

    if (username && !usernames.has(username)) {
      usernames.add(username);
      console.log(`🔍 Found username: @${username}`);
    } else {
      console.log(`⚠️ Failed to extract username from: ${link}`);
    }

    await randomDelay(50, 150); // tiny delay to look human
  }

  console.log(`✅ Extracted ${usernames.size} usernames from location`);
  return Array.from(usernames);
}


async function watchAndLikeStory(page, username) {
  const url = `https://www.instagram.com/stories/${username}/`;
  console.log(`👀 Visiting stories: ${url}`);

  // Load stories page
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
  } catch {
    console.log(`⚠️ Could not load ${url} — skipping`);
    return true;
  }

  // ✅ Wait 2–3 sec for possible redirect to profile
  await delay(2000);

  const currentUrl = page.url();
  if (!currentUrl.includes("/stories/")) {
    console.log(`❌ No story — redirected to profile, skip fallback clicks`);
    return true; // ⏩ Skip to next user
  }

  console.log(`✅ Story confirmed — safe to fallback click`);

  // Continue with fallback clicks...

  await page.evaluate(() => {
    if (document.getElementById("fake-cursor")) return;
    const cursor = document.createElement("div");
    cursor.id = "fake-cursor";
    cursor.style.position = "fixed";
    cursor.style.width = "20px";
    cursor.style.height = "20px";
    cursor.style.border = "2px solid red";
    cursor.style.borderRadius = "50%";
    cursor.style.zIndex = "9999";
    cursor.style.pointerEvents = "none";
    cursor.style.transition = "top 0.05s, left 0.05s";
    document.body.appendChild(cursor);
  });

  const moveCursor = async (x, y) => {
    await page.evaluate((x, y) => {
      const c = document.getElementById('fake-cursor');
      if (c) {
        c.style.left = `${x}px`;
        c.style.top = `${y}px`;
      }
    }, x, y);
    await page.mouse.move(x, y);
  };

  let opened = false;

  for (let i = 1; i <= 20; i++) {
    const x = 595 + Math.floor(Math.random() * 30);
    const y = 455 + Math.floor(Math.random() * 20);
    await moveCursor(x, y);
    await page.mouse.click(x, y);
    await delay(50);

    const like = await page.$('svg[aria-label="Like"]');
    const close = await page.$('button[aria-label="Close"]');
    if (like || close) {
      opened = true;
      console.log(`✅ Fallback click worked on try ${i}`);
      break;
    }
  }

  if (!opened) {
    console.log(`❌ No story opened for @${username}`);
    return true;
  }

  const maxStories = 1 + Math.floor(Math.random() * 2);
  for (let i = 0; i < maxStories; i++) {
    const nextBtn = await page.$('button[aria-label="Next"]');
    if (nextBtn) {
      await nextBtn.click();
      console.log(`➡️ Next story`);
      await randomDelay(100, 300);
    } else {
      console.log(`⏹️ No more stories`);
      break;
    }
  }

  await randomDelay(100, 500);
  return true;
}
  

function isSleepTime() {
  const now = dayjs().tz("Asia/Kolkata");
  const h = now.hour();
  return h >= 22 || h < 08;
}

// ------------------- SCRAPER ACCOUNT -------------------
async function runScrapingAccount(account) {
  const browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 800 });
  await page.setUserAgent("Mozilla/5.0");

  try {
    const hasSession = await loadSession(page, account.sessionFile);
    if (!hasSession) await login(page, account);

    const usernames = await scrapeUsernames(page, "", 50); // ✅ up to 50 fresh usernames
    for (const username of usernames) {
      await addUsernameIfNotExists(username); // ✅ add only if new
      await randomDelay(100, 300);
    }
  } catch (err) {
    console.error(err);
  } finally {
    await browser.close();
  }
}

// ------------------- MAIN ACCOUNT -------------------
async function runMainAccount() {
  const local = fs.existsSync(USERNAMES) ? fs.readFileSync(USERNAMES, "utf8") : "";
  const usernames = local.split("\n").map(l => l.trim()).filter(Boolean).slice(0, 40); // ✅ always top 40

  let browser, page;

  browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox"] });
  page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 800 });
  await page.setUserAgent("Mozilla/5.0");

  const hasSession = await loadSession(page, MAIN_ACCOUNT.sessionFile);
  await browser.close();

  if (!hasSession) {
    const proxyUrl = `${proxy.type}://${proxy.ip}:${proxy.port}`;
    browser = await puppeteer.launch({
      headless: "new",
      args: ["--no-sandbox", `--proxy-server=${proxyUrl}`]
    });
    page = await browser.newPage();
    await page.authenticate({
      username: proxy.username,
      password: proxy.password
    });
    await page.setViewport({ width: 1200, height: 800 });
    await page.setUserAgent("Mozilla/5.0");

    try {
      await login(page, MAIN_ACCOUNT);
    } catch (err) {
      console.error("❌ Login with proxy failed:", err.message);
    } finally {
      await browser.close();
    }
  }

  browser = await puppeteer.launch({ headless: "new", args: ["--no-sandbox"] });
  page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 800 });
  await page.setUserAgent("Mozilla/5.0");

  const hasSessionAgain = await loadSession(page, MAIN_ACCOUNT.sessionFile);
  if (!hasSessionAgain) {
    console.log("❌ Session still missing → abort");
    await browser.close();
    return;
  }

  try {
    for (const username of usernames) {
      await watchAndLikeStory(page, username);
      await randomDelay(500, 1000);
    }
  } catch (err) {
    console.error(err);
  } finally {
    await browser.close();
  }
}

async function takeBreak(minutes) {
  console.log(`⏸ [BREAK] Taking ${minutes} min break...`);
  await delay(minutes * 60 * 1000);
  console.log(`⏱️ [BREAK] Break completed`);
}

// ------------------- MAIN LOOP -------------------
(async () => {
  let lastLongBreak = Date.now();
  while (true) {
    if (isSleepTime()) {
      console.log(`🌙 Sleeping 30 min`);
      await delay(30 * 60 * 1000);
      continue;
    }

    const now = Date.now();
    if (now - lastLongBreak > 60 * 60 * 1000) {
      await takeBreak(10 + Math.floor(Math.random() * 6));
      lastLongBreak = Date.now();
      continue;
    }

    const randomScraper = SCRAPING_ACCOUNTS[Math.floor(Math.random() * SCRAPING_ACCOUNTS.length)];
    await runScrapingAccount(randomScraper);
    await takeBreak(0);

    await runMainAccount();
    await takeBreak(0);

    console.log(`🔄 Cycle done`);
  }
})();
