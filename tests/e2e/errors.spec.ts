import { expect, test } from "@playwright/test";

test.describe("error paths", () => {
  test("unknown model slug returns 404 page", async ({ page }) => {
    const res = await page.goto("/models/does-not-exist");
    expect(res?.status()).toBe(404);
  });

  test("export API rejects path traversal", async ({ request }) => {
    const res = await request.post("/api/export", {
      data: { model: "../etc/passwd.scad" },
    });
    expect(res.status()).toBe(403);
  });

  test("export API rejects unknown model file", async ({ request }) => {
    const res = await request.post("/api/export", {
      data: { model: "models/does_not_exist.scad" },
    });
    expect(res.status()).toBe(404);
  });

  test("export API rejects unknown param key", async ({ request }) => {
    const res = await request.post("/api/export", {
      data: {
        model: "models/smoke_motor_mount.scad",
        params: { made_up_param: 42 },
      },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.error).toContain("unknown param");
  });

  test("thumbnail API rejects hostile slug", async ({ request }) => {
    const res = await request.get("/api/thumbnail?model=../etc/passwd");
    expect(res.status()).toBe(403);
  });
});
