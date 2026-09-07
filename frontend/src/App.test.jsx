import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import App from "./App.jsx";
import { STORAGE_KEY } from "./predictionStorage.js";


const health = {
  status: "ok",
  model: "CatBoost_Pct",
  version: "V2_cleaned",
  explainability: "CatBoost TreeSHAP (exact)",
};

const regions = {
  status: "pending_mapping",
  eligible_factory_count: 104,
  mapped_factory_count: 104,
  verified_factory_count: 0,
  coverage_pct: 0,
  districts: [],
  tea_growing_regions: [],
  elevation_categories: [],
};

const factories = [
  {
    Factory: "BF0143",
    FactoryName: "Templevally",
    latest_reasonable_price: 192.438082,
    latest_data_month: "2025-12-01",
    latest_prediction_month: "2026-01-01",
  },
  {
    Factory: "MF0001",
    FactoryName: "Earlier Factory",
    latest_reasonable_price: 150,
    latest_data_month: "2020-05-01",
    latest_prediction_month: "2020-06-01",
  },
];

const prediction = {
  factory: "BF0143",
  factory_name: "Templevally",
  feature_month: "2025-12-01",
  prediction_month: "2026-01-01",
  current_reasonable_price: 192.438082,
  predicted_reasonable_price: 203.995937,
  approx_lower_90: 177.98,
  approx_upper_90: 230.01,
  model: "CatBoost_Pct",
  target_mode: "pct",
  reliability: "HIGH",
  feature_completeness_pct: 100,
  reliable_history_months: 88,
  production_available: true,
  warnings: [],
  price_history: [
    { month: "2025-11-01", price: 207.98 },
    { month: "2025-12-01", price: 192.44 },
  ],
  market_context: {
    colombo_tea_usd_per_kg: 3.95,
    world_tea_usd_per_kg: 2.88,
    usd_lkr: 304.28,
    rainfall_mm: 210.08,
  },
  expected_leaf_kg: 1250,
  estimated_gross_earnings_lkr: 254994.92,
  gross_earnings_lower_90_lkr: 222475,
  gross_earnings_upper_90_lkr: 287512.5,
  earnings_type: "gross",
  explanation: {
    available: true,
    method: "CatBoost TreeSHAP (exact)",
    baseline_price: 194.14,
    positive_drivers: [
      { feature: "target_month", label: "Forecast seasonality", impact_lkr: 1.91 },
    ],
    negative_drivers: [
      { feature: "NetAvg", label: "Net auction average", impact_lkr: -1.19 },
    ],
    note: "Model associations, not proof of causation.",
  },
};

function response(payload, ok = true, status = ok ? 200 : 400) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(payload) });
}

function mockApi({ predictionResponse = prediction, predictionOk = true } = {}) {
  const fetchMock = vi.fn((url, options = {}) => {
    if (url.endsWith("/health")) return response(health);
    if (url.endsWith("/factories")) return response(factories);
    if (url.endsWith("/regions")) return response(regions);
    if (url.endsWith("/evaluation/status")) return response({ collection_enabled: false, response_count: 0 });
    if (url.endsWith("/estimate-earnings") && options.method === "POST") {
      return response(
        predictionOk ? predictionResponse : { detail: predictionResponse },
        predictionOk,
      );
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("TeaReasonable application", () => {
  beforeEach(() => {
    mockApi();
  });

  test("loads factories and synchronizes each factory's supported month", async () => {
    const user = userEvent.setup();
    render(<App />);

    const factorySelect = await screen.findByLabelText("Factory");
    const monthInput = screen.getByLabelText("Prediction month");
    expect(factorySelect).toHaveValue("BF0143");
    expect(monthInput).toHaveValue("2026-01");

    await user.selectOptions(factorySelect, "MF0001");
    expect(monthInput).toHaveValue("2020-06");
  });

  test("submits a prediction, renders results, and persists it for refresh", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByLabelText("Factory");
    await user.click(screen.getByRole("button", { name: /predict price & earnings/i }));

    expect(await screen.findByRole("heading", { name: /Templevally/i })).toBeInTheDocument();
    expect(screen.getByText("LKR 204.00", { exact: false })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /why the model predicted/i })).toBeInTheDocument();
    expect(JSON.parse(window.sessionStorage.getItem(STORAGE_KEY))).toMatchObject({
      factory: "BF0143",
      predicted_reasonable_price: 203.995937,
    });
  });

  test("restores a saved result after a page refresh", async () => {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(prediction));
    window.location.hash = "results";

    render(<App />);

    expect(await screen.findByRole("heading", { name: /Templevally/i })).toBeInTheDocument();
    expect(screen.queryByText("No forecast yet")).not.toBeInTheDocument();
  });

  test("shows the API detail when a prediction is blocked", async () => {
    vi.unstubAllGlobals();
    mockApi({ predictionResponse: "No previous-month feature row.", predictionOk: false });
    const user = userEvent.setup();
    render(<App />);

    await screen.findByLabelText("Factory");
    await user.click(screen.getByRole("button", { name: /predict price & earnings/i }));

    expect(await screen.findByText("No previous-month feature row.")).toBeInTheDocument();
  });
});
