const STORAGE_KEY = "tea-reasonable-ai:last-prediction:v1";

function defaultStorage() {
  try {
    return globalThis.sessionStorage;
  } catch {
    return null;
  }
}

export function isPredictionPayload(value) {
  return Boolean(
    value
      && typeof value === "object"
      && typeof value.factory === "string"
      && typeof value.prediction_month === "string"
      && Number.isFinite(value.predicted_reasonable_price),
  );
}

export function loadPrediction(storage = defaultStorage()) {
  if (!storage) return null;
  try {
    const value = JSON.parse(storage.getItem(STORAGE_KEY));
    if (isPredictionPayload(value)) return value;
    storage.removeItem(STORAGE_KEY);
  } catch {
    try {
      storage.removeItem(STORAGE_KEY);
    } catch {
      // Storage can be disabled by browser privacy settings.
    }
  }
  return null;
}

export function savePrediction(prediction, storage = defaultStorage()) {
  if (!storage || !isPredictionPayload(prediction)) return false;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(prediction));
    return true;
  } catch {
    return false;
  }
}

export { STORAGE_KEY };
