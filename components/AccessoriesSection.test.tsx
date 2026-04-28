// @vitest-environment jsdom

import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import {
  AccessoriesSection,
  formatFileSize,
  type DetailPageAccessory,
} from "./AccessoriesSection";

afterEach(() => cleanup());

const seed: DetailPageAccessory = {
  slug: "openconnect-flush-mid-coin",
  title: "Openconnect Flush Mid Coin",
  blurb: "Mounts cylindrical holders to a Multiboard.",
  downloadUrl: "/api/accessories/openconnect-flush-mid-coin",
  fileSize: 628484,
};

describe("AccessoriesSection", () => {
  it("renders nothing when no accessories are provided", () => {
    const { queryByTestId } = render(<AccessoriesSection accessories={[]} />);
    expect(queryByTestId("accessories-section")).toBeNull();
  });

  it("renders the seed entry with a working download link", () => {
    const { getByTestId, getAllByTestId, getByText } = render(
      <AccessoriesSection accessories={[seed]} />,
    );
    expect(getByTestId("accessories-section")).toBeTruthy();
    const rows = getAllByTestId("accessory-row");
    expect(rows).toHaveLength(1);

    const link = rows[0].querySelector("a");
    expect(link).not.toBeNull();
    expect(link!.getAttribute("href")).toBe(seed.downloadUrl);
    expect(link!.hasAttribute("download")).toBe(true);
    expect(link!.getAttribute("download")).toBe(`${seed.slug}.stl`);

    expect(getByText(seed.title)).toBeTruthy();
    expect(getByText(seed.blurb)).toBeTruthy();
  });

  it("renders multiple entries", () => {
    const second: DetailPageAccessory = {
      ...seed,
      slug: "another-thing",
      title: "Another Thing",
      blurb: "Another accessory",
    };
    const { getAllByTestId } = render(
      <AccessoriesSection accessories={[seed, second]} />,
    );
    expect(getAllByTestId("accessory-row")).toHaveLength(2);
  });

  it("renders attribution line when provided", () => {
    const withAttr: DetailPageAccessory = {
      ...seed,
      attribution: "Designed by Jane Doe (CC-BY)",
    };
    const { getByText } = render(<AccessoriesSection accessories={[withAttr]} />);
    expect(getByText("Designed by Jane Doe (CC-BY)")).toBeTruthy();
  });
});

describe("formatFileSize", () => {
  it("formats bytes/KB/MB at sane breakpoints", () => {
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(2048)).toBe("2.0 KB");
    expect(formatFileSize(1024 * 1024 * 1.5)).toBe("1.5 MB");
  });
});
