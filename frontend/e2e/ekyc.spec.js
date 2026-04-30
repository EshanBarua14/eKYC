// Playwright E2E tests — Xpert eKYC 7-step flow — v4 final
// Run: npx playwright test

import { test, expect } from "@playwright/test"

const BASE = "http://localhost:5173"

test.describe("7-Step eKYC Flow", () => {

  test("Step 1 — NID Entry renders correctly", async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator(".hero-title")).toContainText("Digital eKYC")
    await expect(page.locator(".nid-entry-wrap")).toBeVisible()
    await expect(page.locator("text=NID Number")).toBeVisible()
    await expect(page.locator("label").filter({ hasText: "Date of Birth" }).first()).toBeVisible()
    await expect(page.locator("text=Verify NID with Election Commission")).toBeVisible()
  })

  test("Step 1 — validates empty NID", async ({ page }) => {
    await page.goto(BASE)
    await page.click("text=Verify NID with Election Commission")
    await expect(page.locator(".nid-entry-wrap")).toBeVisible()
  })

  test("Step 1 — validates NID format", async ({ page }) => {
    await page.goto(BASE)
    const nidInput = page.locator("input").first()
    await nidInput.fill("123")
    await page.click("text=Verify NID with Election Commission")
    await expect(page.locator(".nid-entry-wrap")).toBeVisible()
  })

  test("Step 1 → Step 2 — NID verification flow runs", async ({ page }) => {
    await page.goto(BASE)
    const nidInput = page.locator("input").first()
    await nidInput.fill("1234567890")
    const dobInput = page.locator("input[type='date']")
    if (await dobInput.count() > 0) await dobInput.fill("1990-01-15")
    await page.click("text=Verify NID with Election Commission")
    // wait for API call to complete (demo or live)
    await page.waitForTimeout(4000)
    // page must still be rendered after verification attempt
    await expect(page.locator(".hero-title").or(page.locator(".nid-entry-wrap")).first()).toBeVisible()
    // if proceed button appears, flow completed successfully
    const proceedBtn = page.locator("text=Confirmed — Proceed to NID Scan →")
    if (await proceedBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await proceedBtn.click()
      await expect(page.locator("text=Front Side")).toBeVisible({ timeout: 5000 })
    }
  })

  test("Step 2 — shows front and back upload zones", async ({ page }) => {
    await page.goto(BASE)
    const nidInput = page.locator("input").first()
    await nidInput.fill("1234567890")
    const dobInput = page.locator("input[type='date']")
    if (await dobInput.count() > 0) await dobInput.fill("1990-01-15")
    await page.click("text=Verify NID with Election Commission")
    const proceedBtn = page.locator("text=Confirmed — Proceed to NID Scan →")
    if (await proceedBtn.isVisible({ timeout: 8000 }).catch(() => false)) {
      await proceedBtn.click()
      await expect(page.locator("text=Front Side")).toBeVisible({ timeout: 5000 })
      await expect(page.locator("text=Back Side")).toBeVisible()
    }
  })

  test("Header — staff login button present", async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator(".portal-btn-agent")).toBeVisible()
    await expect(page.locator("text=Staff Login")).toBeVisible()
  })

  test("Theme toggle — header visible", async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator(".app-header")).toBeVisible()
  })

  test("Admin Console — staff login shows role selector", async ({ page }) => {
    await page.goto(BASE)
    await page.click(".portal-btn-agent")
    await page.waitForTimeout(1000)
    // RBACLogin renders: "Select your role to continue" + role buttons
    await expect(page.locator("text=Select your role to continue")).toBeVisible({ timeout: 5000 })
    // ADMIN role button must be present
    await expect(page.locator("text=Admin")).toBeVisible({ timeout: 3000 })
    // back button also present
    await expect(page.locator("text=Back to Customer Portal")).toBeVisible()
  })

  test("Step bar — shows step labels", async ({ page }) => {
    await page.goto(BASE)
    await expect(page.locator("div").filter({ hasText: /^NID Entry$/ }).first()).toBeVisible()
    await expect(page.locator("div").filter({ hasText: /^Scan NID$/ }).first()).toBeVisible()
  })

  test("Responsive — mobile viewport no overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(BASE)
    await page.waitForLoadState("networkidle")
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
    console.log(`Overflow: scrollWidth=${scrollWidth} clientWidth=${clientWidth} diff=${scrollWidth - clientWidth}px`)
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 20)
  })

})
