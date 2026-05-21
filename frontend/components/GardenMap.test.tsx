import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { GardenMap } from "./GardenMap";

const property = {
  id: 1,
  address_raw: "123 Garden Lane",
  normalized_address: "123 Garden Lane, Detroit, MI",
  latitude: 42.3314,
  longitude: -83.0458
};

afterEach(cleanup);

describe("GardenMap", () => {
  it("keeps draw instructions out of the map overlay", () => {
    render(<GardenMap property={property} onPolygon={() => undefined} />);

    expect(screen.queryByText(/Step 1: Confirm property and zoom in/i)).toBeNull();
    expect(screen.queryByText(/Click each corner of the garden polygon/i)).toBeNull();
    expect(screen.getByText(/North ↑/)).toBeTruthy();
  });
});
