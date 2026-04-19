// Playwright E2E tests — Xpert eKYC 7-step flow
// Run: npx playwright test

import { test, expect } from "@playwright/test"

const BASE = "http://localhost:5173"

test.describe("7-Step eKYC Flow", () => {

  test("Step 1 — NID Entry renders correctly", async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator("h1")).toContainText("Digital eKYC")
    await expect(page.locator(".step-circle-active")).toContainText("1")
    await expect(page.locator("text=NID Number")).toBeVisible()
    await expect(page.locator("text=Date of Birth")).toBeVisible()
    await expect(page.locator("text=Verify NID")).toBeVisible()
  })

  test("Step 1 — validates empty NID", async ({ page }) => {
    await page.goto(BASE)
    await page.click("text=Verify NID with Election Commission")
    await expect(page.locator("text=valid NID number")).toBeVisible()
  })

  test("Step 1 — validates NID format", async ({ page }) => {
    await page.goto(BASE)
    await page.fill("input[placeholder*='NID']", "123")  // too short
    await page.click("text=Verify NID with Election Commission")
    await expect(page.locator("text=valid NID number")).toBeVisible()
  })

  test("Step 1 → Step 2 — valid NID proceeds", async ({ page }) => {
    await page.goto(BASE)
    await page.fill("input[placeholder*='NID']", "1234567890")
    await page.fill("input[type='date']", "1990-01-15")
    await page.click("text=Verify NID with Election Commission")
    await expect(page.locator("text=NID Found")).toBeVisible({ timeout: 10000 })
    await page.click("text=Confirmed — Proceed to NID Scan")
    await expect(page.locator(".step-circle-active")).toContainText("2")
    await expect(page.locator("text=Upload NID Card")).toBeVisible()
  })

  test("Step 2 — shows front and back upload zones", async ({ page }) => {
    await page.goto(BASE)
    // Navigate to step 2
    await page.fill("input[placeholder*='NID']", "1234567890")
    await page.fill("input[type='date']", "1990-01-15")
    await page.click("text=Verify NID with Election Commission")
    await page.click("text=Confirmed — Proceed", { timeout: 10000 })
    await expect(page.locator("text=Front Side")).toBeVisible()
    await expect(page.locator("text=Back Side")).toBeVisible()
  })

  test("Header — all portal buttons present", async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator(".portal-btn-agent")).toBeVisible()
    await expect(page.locator(".portal-btn-admin")).toBeVisible()
    await expect(page.locator(".portal-btn-compliance")).toBeVisible()
  })

  test("Theme toggle — persists across reload", async ({ page }) => {
    await page.goto(BASE)
    await page.click(".theme-toggle")
    await page.reload()
    const theme = await page.evaluate(() =>
      document.documentElement.getAttribute("data-theme"))
    expect(theme).toBe("dark")
    // Reset
    await page.click(".theme-toggle")
  })

  test("Admin Console — loads correctly", async ({ page }) => {
    await page.goto(BASE)
    await page.click(".portal-btn-admin")
    await expect(page.locator("text=Admin Console")).toBeVisible()
    await expect(page.locator("text=Institutions")).toBeVisible()
  })

  test("Compliance Dashboard — loads correctly", async ({ page }) => {
    await page.goto(BASE)
    await page.click(".portal-btn-compliance")
    await expect(page.locator("text=Compliance")).toBeVisible()
    await expect(page.locator("text=Posture")).toBeVisible()
  })

  test("Agent Portal — loads correctly", async ({ page }) => {
    await page.goto(BASE)
    await page.click(".portal-btn-agent")
    await expect(page.locator("text=Agent")).toBeVisible()
  })

  test("Step bar — shows 7 steps", async ({ page }) => {
    await page.goto(BASE)
    const steps = await page.locator(".step-circle").count()
    expect(steps).toBe(7)
  })

  test("Responsive — mobile viewport renders without overflow", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto(BASE)
    await expect(page.locator("h1")).toBeVisible()
    await expect(page.locator(".app-header")).toBeVisible()
    // Check no horizontal scroll
    const scrollWidth = await page.evaluate(() => document.body.scrollWidth)
    const clientWidth = await page.evaluate(() => document.body.clientWidth)
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 5)
  })

})
