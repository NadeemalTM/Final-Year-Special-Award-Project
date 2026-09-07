import { expect, test } from "vitest";

import {
  STORAGE_KEY,
  isPredictionPayload,
  loadPrediction,
  savePrediction,
} from "./predictionStorage.js";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

const prediction = {
  factory: "BF0143",
  prediction_month: "2026-01-01",
  predicted_reasonable_price: 203.995,
};

test("recognizes a valid persisted prediction", () => {
  expect(isPredictionPayload(prediction)).toBe(true);
  expect(isPredictionPayload({ ...prediction, predicted_reasonable_price: "204" })).toBe(false);
});

test("saves and restores the last prediction", () => {
  const storage = memoryStorage();
  expect(savePrediction(prediction, storage)).toBe(true);
  expect(loadPrediction(storage)).toEqual(prediction);
});

test("removes corrupt or incomplete stored data", () => {
  const corrupt = memoryStorage({ [STORAGE_KEY]: "not-json" });
  expect(loadPrediction(corrupt)).toBeNull();
  expect(corrupt.getItem(STORAGE_KEY)).toBeNull();

  const incomplete = memoryStorage({ [STORAGE_KEY]: JSON.stringify({ factory: "BF0143" }) });
  expect(loadPrediction(incomplete)).toBeNull();
  expect(incomplete.getItem(STORAGE_KEY)).toBeNull();
});
