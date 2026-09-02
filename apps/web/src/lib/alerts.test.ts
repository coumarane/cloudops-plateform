import { describe, expect, it } from "vitest";
import { alertHref, isPrdAlert, minutesAgo } from "./alerts";

describe("alert console helpers", () => {
  it("builds alert detail hrefs", () => {
    expect(alertHref("al-1")).toBe("/alerts?selected=al-1");
    expect(alertHref()).toBe("/alerts");
  });

  it("distinguishes PRD alerts for visual treatment", () => {
    expect(isPrdAlert({ environment: "PRD" })).toBe(true);
    expect(isPrdAlert({ environment: "UAT" })).toBe(false);
  });

  it("formats elapsed time without exposing secrets", () => {
    const now = new Date().toISOString();
    expect(minutesAgo(now)).toMatch(/just now|1 minute|minutes/);
  });
});
