const { test, expect } = require('@playwright/test');

test('B01 canceled checkout names the package and confirms no payment', async ({ page }) => {
  await page.goto('/pricing?checkout=cancelled&plan=pro');
  await expect(page.getByText(/Pro checkout was canceled.*No payment was taken/i)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Pro' })).toBeVisible();
});

test('C01-C04 pricing contract is visible before checkout', async ({ page }) => {
  await page.goto('/pricing');
  for (const [plan, price] of [['Squares Plus', '$10'], ['Commish', '$39'], ['Pro', '$79'], ['Club', '$129'], ['Club Unlimited', '$249']]) {
    const card = page.getByRole('heading', { name: plan, exact: true }).locator('xpath=ancestor::article[1]');
    await expect(card).toContainText(price);
  }
});
