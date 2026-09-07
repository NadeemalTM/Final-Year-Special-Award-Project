import { useEffect, useMemo, useState } from "react";
import { loadPrediction, savePrediction } from "./predictionStorage.js";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "/api")
).replace(/\/$/, "");

const money = new Intl.NumberFormat("en-LK", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function Icon({ children, className = "" }) {
  return (
    <span className={`material-symbols-outlined ${className}`} aria-hidden="true">
      {children}
    </span>
  );
}

function formatMonth(value, short = false) {
  if (!value) return "—";
  const [year, month] = value.slice(0, 7).split("-").map(Number);
  return new Intl.DateTimeFormat("en-LK", {
    month: short ? "short" : "long",
    year: "numeric",
  }).format(new Date(year, month - 1, 1));
}

function getErrorMessage(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join("; ");
  }
  return fallback;
}

async function apiRequest(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(getErrorMessage(payload, `The API returned status ${response.status}.`));
  }
  return payload;
}

function Header({ page, health, loading, onNavigate }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const links = [
    ["dashboard", "Dashboard"],
    ["predict", "Price Prediction"],
    ["compare", "Compare Factories"],
    ["evaluation", "Research Evaluation"],
    ["about", "How it Works"],
  ];

  function navigate(target) {
    setMenuOpen(false);
    onNavigate(target);
  }

  return (
    <header className="site-header">
      <div className="nav-shell">
        <button className="wordmark" type="button" onClick={() => navigate("dashboard")}>
          <span className="wordmark-icon"><Icon>eco</Icon></span>
          <span>TeaReasonable AI</span>
        </button>

        <nav className={`nav-links ${menuOpen ? "open" : ""}`} aria-label="Primary navigation">
          {links.map(([target, label]) => {
            const active = target === "predict" ? page === "results" : page === target;
            return (
              <button className={active ? "active" : ""} key={target} type="button" onClick={() => navigate(target)}>
                {label}
              </button>
            );
          })}
        </nav>

        <div className="nav-actions">
          <a className={`api-indicator ${health ? "online" : ""}`} href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer" aria-label="Open API documentation" title={health ? `API connected · ${health.model}` : "API unavailable"}>
            <span className="status-dot" />
            <Icon>database</Icon>
            <span className="api-label">{health ? "Connected" : loading ? "Connecting" : "Offline"}</span>
          </a>
          <button className="icon-button help-button" type="button" onClick={() => navigate("about")} aria-label="How it works"><Icon>help</Icon></button>
          <button className="icon-button menu-button" type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-label="Toggle navigation"><Icon>{menuOpen ? "close" : "menu"}</Icon></button>
        </div>
      </div>
    </header>
  );
}

function Footer({ health, onNavigate }) {
  return (
    <footer className="site-footer">
      <div className="footer-shell">
        <strong>TeaReasonable AI</strong>
        <p>© {new Date().getFullYear()} TeaReasonable AI. Decision-support tool only.</p>
        <div>
          <button type="button" onClick={() => onNavigate("about")}>Methodology</button>
          <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">API Docs</a>
          {health?.version && <span>Model {health.version}</span>}
        </div>
      </div>
    </footer>
  );
}

function HeroVisual({ factoryCount }) {
  return (
    <div className="hero-visual" aria-hidden="true">
      <picture className="hero-estate-picture">
        <img src="/images/ceylon-estate-hero.jpg" alt="" width="1440" height="960" fetchPriority="high" decoding="async" />
      </picture>
      <div className="hero-image-shade" />
      <div className="estate-label"><Icon>landscape</Icon><span>Ceylon highlands</span></div>
      <img className="hero-leaf-sprig" src="/images/tea-sprig.png" alt="" width="768" height="512" decoding="async" />
      <span className="floating-leaf leaf-one" />
      <span className="floating-leaf leaf-two" />
      <span className="floating-leaf leaf-three" />
      <span className="floating-leaf leaf-four" />
      <div className="visual-stat visual-stat-top"><Icon>monitoring</Icon><span><b>1 month</b> forecast horizon</span></div>
      <div className="visual-stat visual-stat-bottom"><Icon>verified</Icon><span><b>{factoryCount || "—"}</b> eligible factories</span></div>
      <div className="estate-caption"><span>Estate data</span><strong>From leaf to forecast</strong></div>
    </div>
  );
}

function Dashboard({ health, factories, factory, setFactory, targetMonth, setTargetMonth, expectedLeafKg, setExpectedLeafKg, loading, submitting, connectionError, predictionError, onSubmit, onCompare }) {
  const selected = factories.find((item) => String(item.Factory) === factory);

  function handleFactoryChange(event) {
    const value = event.target.value;
    const nextFactory = factories.find((item) => String(item.Factory) === value);
    setFactory(value);
    if (nextFactory?.latest_prediction_month) {
      setTargetMonth(nextFactory.latest_prediction_month.slice(0, 7));
    }
  }

  return (
    <main className="page dashboard-page">
      <section className="dashboard-hero">
        <div className="hero-copy">
          <div className="data-status"><Icon>verified</Icon><span>Data up to date</span><i /><span>Latest: {formatMonth(selected?.latest_data_month, true)}</span></div>
          <h1>Predict next month&apos;s tea reasonable price.</h1>
          <p>Forecast next-month factory Reasonable Prices, estimate gross tea-owner earnings, and compare price alternatives using verified historical, production, weather, and market signals.</p>
          <div className="hero-actions">
            <button className="primary-button" type="button" onClick={() => document.getElementById("prediction-form")?.scrollIntoView({ behavior: "smooth" })}>Predict a price <Icon>arrow_forward</Icon></button>
            <button className="secondary-button" type="button" onClick={onCompare}>Compare factories</button>
          </div>
        </div>
        <HeroVisual factoryCount={factories.length} />
      </section>

      {connectionError && <div className="alert error-alert" role="alert"><Icon>cloud_off</Icon><div><strong>Prediction service unavailable</strong><span>{connectionError}</span></div></div>}

      <section className="summary-grid" aria-label="Forecast overview">
        <article className="summary-card"><div><span>Latest factory price</span><Icon>payments</Icon></div><strong>{selected?.latest_reasonable_price ? `LKR ${money.format(selected.latest_reasonable_price)}` : "—"}</strong><small>{selected ? `${selected.FactoryName} · per kg` : "Select a factory"}</small></article>
        <article className="summary-card"><div><span>Eligible factories</span><Icon>factory</Icon></div><strong>{factories.length || "—"}</strong><small>Passed reliable-history checks</small></article>
        <article className="summary-card"><div><span>Forecast month</span><Icon>calendar_month</Icon></div><strong>{formatMonth(targetMonth)}</strong><small>One-month-ahead window</small></article>
        <article className="summary-card"><div><span>Prediction model</span><Icon>analytics</Icon></div><strong>{health?.model?.replace("_", " ") || "CatBoost"}</strong><small>Approximate 90% uncertainty range</small></article>
      </section>

      <section className="prediction-entry" id="prediction-form">
        <img className="prediction-leaf-accent" src="/images/tea-sprig.png" alt="" aria-hidden="true" width="768" height="512" loading="lazy" decoding="async" />
        <div className="entry-intro">
          <span className="section-icon"><Icon>search_insights</Icon></span>
          <div><p className="eyebrow">Price prediction</p><h2>Generate a factory forecast</h2><p>Select an eligible factory and the supported next month. Results open in a focused analysis view.</p></div>
        </div>
        <form className="prediction-controls" onSubmit={onSubmit}>
          <label htmlFor="factory-select"><span>Factory</span><div className="control-wrap"><Icon>factory</Icon><select id="factory-select" aria-label="Factory" value={factory} onChange={handleFactoryChange} disabled={loading || !factories.length} required>{!factories.length && <option value="">No factories loaded</option>}{factories.map((item) => <option value={item.Factory} key={item.Factory}>{item.Factory} — {item.FactoryName}</option>)}</select><Icon className="chevron">expand_more</Icon></div></label>
          <label htmlFor="prediction-month"><span>Prediction month</span><div className="control-wrap month-control"><Icon>calendar_month</Icon><input id="prediction-month" aria-label="Prediction month" type="month" min="2015-02" max="2100-12" value={targetMonth} onChange={(event) => setTargetMonth(event.target.value)} required /></div></label>
          <label htmlFor="leaf-quantity"><span>Expected tea leaves (kg)</span><div className="control-wrap"><Icon>scale</Icon><input id="leaf-quantity" aria-label="Expected tea leaves kg" type="number" min="0.01" step="0.01" value={expectedLeafKg} onChange={(event) => setExpectedLeafKg(event.target.value)} placeholder="e.g. 1250" required /></div></label>
          <button className="primary-button prediction-button" type="submit" disabled={submitting || loading || !factory}>{submitting ? <><span className="spinner" /> Calculating…</> : <>Predict price & earnings <Icon>magic_button</Icon></>}</button>
        </form>
        {predictionError && <div className="inline-error" role="alert"><Icon>error</Icon><span>{predictionError}</span></div>}
      </section>
    </main>
  );
}

function PriceChart({ history = [], predicted, predictionMonth }) {
  const series = [...history.map((item) => ({ ...item, predicted: false })), { month: predictionMonth, price: predicted, predicted: true }];
  const prices = series.map((item) => Number(item.price)).filter(Number.isFinite);
  if (prices.length < 2) return <div className="chart-empty">Price history is unavailable.</div>;
  const width = 760;
  const height = 260;
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const padding = Math.max((max - min) * 0.2, 10);
  const low = min - padding;
  const high = max + padding;
  const point = (item, index) => ({ x: (index / (series.length - 1)) * width, y: height - ((item.price - low) / (high - low)) * height });
  const points = series.map(point);
  const historicalPath = points.slice(0, -1).map((item) => `${item.x},${item.y}`).join(" ");
  const predictionPath = points.slice(-2).map((item) => `${item.x},${item.y}`).join(" ");
  const last = points.at(-1);
  const previous = points.at(-2);
  const labels = [series[0], series[Math.floor((series.length - 1) / 2)], series.at(-1)];

  return (
    <div className="chart-wrap">
      <div className="chart-y-labels"><span>{money.format(high)}</span><span>{money.format((high + low) / 2)}</span><span>{money.format(low)}</span></div>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Historical and predicted reasonable price trajectory">
        <defs><linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#116c4a" stopOpacity="0.22" /><stop offset="100%" stopColor="#116c4a" stopOpacity="0" /></linearGradient></defs>
        {[0, 0.5, 1].map((value) => <line key={value} x1="0" x2={width} y1={height * value} y2={height * value} className="grid-line" />)}
        <polyline points={historicalPath} className="history-line" />
        <polygon points={`${previous.x},${height} ${previous.x},${previous.y} ${last.x},${last.y} ${last.x},${height}`} className="prediction-fill" />
        <polyline points={predictionPath} className="prediction-line" />
        <line x1={previous.x} x2={previous.x} y1="0" y2={height} className="present-line" />
        <circle cx={previous.x} cy={previous.y} r="4" className="history-dot" />
        <circle cx={last.x} cy={last.y} r="6" className="prediction-dot" />
      </svg>
      <div className="chart-x-labels">{labels.map((item, index) => <span key={`${item.month}-${index}`}>{formatMonth(item.month, true)}</span>)}</div>
      <span className="chart-value" style={{ top: `${Math.max(3, (last.y / height) * 100 - 12)}%` }}>{money.format(predicted)}</span>
    </div>
  );
}

function ContextCard({ icon, label, value }) {
  return <div className="context-card"><div><span>{label}</span><Icon>{icon}</Icon></div><strong>{value ?? "Unavailable"}</strong></div>;
}

function DriverAnalysis({ explanation }) {
  if (!explanation?.available) {
    return (
      <article className="driver-panel panel">
        <div className="panel-title"><h2>Model driver analysis</h2><Icon>psychology_alt</Icon></div>
        <p className="driver-unavailable">Local feature attribution is unavailable for this forecast.</p>
      </article>
    );
  }

  const positive = explanation.positive_drivers || [];
  const negative = explanation.negative_drivers || [];
  const maximum = Math.max(1, ...[...positive, ...negative].map((item) => Math.abs(item.impact_lkr)));

  function group(title, icon, items, direction) {
    return (
      <div className={`driver-group ${direction}`}>
        <h3><Icon>{icon}</Icon>{title}</h3>
        <div className="driver-list">
          {items.map((item) => (
            <div className="driver-row" key={item.feature}>
              <span title={item.label}>{item.label}</span>
              <div className="driver-track"><i style={{ width: `${Math.max(8, Math.abs(item.impact_lkr) / maximum * 100)}%` }} /></div>
              <strong>{item.impact_lkr > 0 ? "+" : ""}{money.format(item.impact_lkr)}</strong>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <article className="driver-panel panel">
      <div className="panel-title"><h2>Why the model predicted this price</h2><span className="method-chip">SHAP</span></div>
      <p className="driver-baseline">Largest SHAP attributions are shown as LKR/kg equivalents relative to the fixed-anchor model baseline of <strong>LKR {money.format(explanation.baseline_price)}</strong>.</p>
      <div className="driver-columns">
        {group("Pushing higher", "arrow_upward", positive, "positive")}
        {group("Pushing lower", "arrow_downward", negative, "negative")}
      </div>
      <p className="driver-note"><Icon>info</Icon>{explanation.note}</p>
    </article>
  );
}

function Results({ prediction, onNewPrediction }) {
  if (!prediction) return <main className="page missing-result"><Icon>query_stats</Icon><h1>No forecast yet</h1><p>Generate a prediction from the dashboard to see the analysis.</p><button className="primary-button" type="button" onClick={onNewPrediction}>Start a prediction</button></main>;

  const delta = prediction.predicted_reasonable_price - prediction.current_reasonable_price;
  const deltaPct = prediction.current_reasonable_price ? delta / prediction.current_reasonable_price * 100 : 0;
  const positive = delta >= 0;
  const context = prediction.market_context || {};

  function exportReport() {
    const blob = new Blob([JSON.stringify(prediction, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${prediction.factory}-${prediction.prediction_month}-forecast.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function printReport() {
    window.print();
  }

  return (
    <main className="page results-page">
      <div className="print-report-header"><strong>TeaReasonable AI</strong><span>Factory price forecast</span></div>
      <section className="results-heading">
        <div><p className="breadcrumb"><button type="button" onClick={onNewPrediction}>Price Prediction</button><Icon>chevron_right</Icon><span>Results</span></p><h1>{prediction.factory_name} <span>({prediction.factory})</span></h1><p>Prediction target: {formatMonth(prediction.prediction_month)}</p></div>
        <div className="results-actions"><button className="secondary-button" type="button" onClick={exportReport}><Icon>data_object</Icon> Export JSON</button><button className="secondary-button" type="button" onClick={printReport}><Icon>picture_as_pdf</Icon> Save PDF</button><button className="primary-button" type="button" onClick={onNewPrediction}><Icon>autorenew</Icon> New prediction</button></div>
      </section>
      <div className="results-layout">
        <div className="results-primary">
          <article className="price-card panel">
            <Icon className="price-watermark">eco</Icon>
            <div className="price-main"><p>Predicted reasonable price</p><div><strong>LKR {money.format(prediction.predicted_reasonable_price)}</strong><span>/ kg</span></div><div className={`delta-chip ${positive ? "positive" : "negative"}`}><Icon>{positive ? "trending_up" : "trending_down"}</Icon><b>{positive ? "+" : ""}LKR {money.format(delta)} ({positive ? "+" : ""}{deltaPct.toFixed(2)}%)</b><span>vs current LKR {money.format(prediction.current_reasonable_price)}</span></div></div>
            <div className="price-meta"><div><span>Approximate 90% prediction range</span><strong>LKR {money.format(prediction.approx_lower_90)} – {money.format(prediction.approx_upper_90)}</strong><div className="range-line"><i /></div></div><div><span>Prediction horizon</span><strong><Icon>calendar_month</Icon>{formatMonth(prediction.prediction_month)}</strong></div></div>
          </article>
          {prediction.estimated_gross_earnings_lkr != null && <article className="earnings-card panel"><div><p className="eyebrow">Tea-owner decision support</p><h2>Estimated gross earnings</h2><p>Based on <strong>{money.format(prediction.expected_leaf_kg)} kg</strong> of expected green tea leaves.</p></div><div className="earnings-value"><strong>LKR {money.format(prediction.estimated_gross_earnings_lkr)}</strong><span>Approx. range LKR {money.format(prediction.gross_earnings_lower_90_lkr)} – {money.format(prediction.gross_earnings_upper_90_lkr)}</span></div><p className="earnings-note"><Icon>info</Icon>Gross estimate only. Labour, fertilizer, transport, deductions and other costs are not subtracted.</p></article>}
          <article className="chart-panel panel"><div className="panel-title"><h2>Price trajectory</h2><div className="chart-legend"><span><i />Historical</span><span><i className="forecast" />Prediction</span></div></div><PriceChart history={prediction.price_history} predicted={prediction.predicted_reasonable_price} predictionMonth={prediction.prediction_month} /></article>
          <DriverAnalysis explanation={prediction.explanation} />
          <article className="quality-panel panel"><div className="panel-title"><h2>Forecast quality</h2><Icon>fact_check</Icon></div><div className="quality-grid"><div><Icon>history</Icon><span>Reliable price history</span><strong>{prediction.reliable_history_months} months</strong></div><div><Icon>inventory_2</Icon><span>Production data</span><strong>{prediction.production_available ? "Available" : "Model-imputed"}</strong></div><div><Icon>date_range</Icon><span>Feature month</span><strong>{formatMonth(prediction.feature_month)}</strong></div></div>{prediction.warnings?.length ? <ul className="warning-list">{prediction.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p className="all-clear"><Icon>check_circle</Icon> All safety and input-quality checks passed.</p>}</article>
        </div>
        <aside className="results-sidebar">
          <article className="panel reliability-card"><div className="panel-title"><h2>Prediction reliability</h2><span className={`reliability ${prediction.reliability.toLowerCase()}`}><Icon>check_circle</Icon>{prediction.reliability}</span></div><div className="completeness"><div><span>Feature completeness</span><strong>{prediction.feature_completeness_pct.toFixed(1)}%</strong></div><div className="progress"><i style={{ width: `${prediction.feature_completeness_pct}%` }} /></div></div><div className="history-note"><Icon>history</Icon><p><strong>Verified historical base</strong><span>{prediction.reliable_history_months} reliable monthly observations support this forecast.</span></p></div></article>
          <article className="panel context-panel"><div className="panel-title"><h2>Macro market context</h2><Icon>public</Icon></div><div className="context-grid"><ContextCard icon="monitoring" label="Colombo tea" value={context.colombo_tea_usd_per_kg != null ? `$${money.format(context.colombo_tea_usd_per_kg)} / kg` : null} /><ContextCard icon="language" label="World tea avg." value={context.world_tea_usd_per_kg != null ? `$${money.format(context.world_tea_usd_per_kg)} / kg` : null} /><ContextCard icon="currency_exchange" label="USD / LKR" value={context.usd_lkr != null ? money.format(context.usd_lkr) : null} /><ContextCard icon="rainy" label="Rainfall" value={context.rainfall_mm != null ? `${money.format(context.rainfall_mm)} mm` : null} /></div></article>
          <details className="panel model-details"><summary><span><Icon>memory</Icon>Model architecture</span><Icon>expand_more</Icon></summary><div><p><span>Algorithm</span><strong>{prediction.model}</strong></p><p><span>Target mode</span><strong>{prediction.target_mode}</strong></p><p><span>Forecast step</span><strong>One month ahead</strong></p></div></details>
        </aside>
      </div>
      <div className="print-report-footer">Approximate 90% prediction range. Decision-support output—not a financial guarantee.</div>
    </main>
  );
}

function CompareFactories({ defaultMonth, defaultQuantity, onOpenFactory, regionInfo }) {
  const [month, setMonth] = useState(defaultMonth || "2026-01");
  const [quantity, setQuantity] = useState(defaultQuantity || "1250");
  const [topN, setTopN] = useState(10);
  const [district, setDistrict] = useState("");
  const [teaRegion, setTeaRegion] = useState("");
  const [elevation, setElevation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [comparison, setComparison] = useState(null);
  const geographyReady = (regionInfo?.verified_factory_count || 0) > 0;

  async function submit(event) {
    event.preventDefault();
    const [year, monthNumber] = month.split("-").map(Number);
    setLoading(true);
    setError("");
    try {
      const payload = await apiRequest("/compare-factories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          year,
          month: monthNumber,
          expected_leaf_kg: Number(quantity),
          top_n: Number(topN),
          district: district || null,
          tea_growing_region: teaRegion || null,
          elevation_category: elevation || null,
          verified_geography_only: Boolean(district || teaRegion || elevation),
        }),
      });
      setComparison(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page compare-page">
      <section className="compare-hero"><div><p className="eyebrow">Factory comparison</p><h1>Compare predicted Reasonable Prices before you decide.</h1><p>Use the same expected leaf quantity across eligible factories to compare next-month price forecasts and estimated gross earnings.</p></div><div className="compare-badge"><Icon>compare_arrows</Icon><strong>Price-first ranking</strong><span>Decision support, not a guarantee</span></div></section>
      <section className="comparison-form panel">
        <form onSubmit={submit}>
          <label><span>Forecast month</span><div className="control-wrap"><Icon>calendar_month</Icon><input aria-label="Comparison month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} required /></div></label>
          <label><span>Expected leaves (kg)</span><div className="control-wrap"><Icon>scale</Icon><input aria-label="Comparison tea leaves kg" type="number" min="0.01" step="0.01" value={quantity} onChange={(e) => setQuantity(e.target.value)} required /></div></label>
          <label><span>Show top</span><div className="control-wrap"><Icon>format_list_numbered</Icon><select aria-label="Top factory count" value={topN} onChange={(e) => setTopN(e.target.value)}><option value="5">5 factories</option><option value="10">10 factories</option><option value="20">20 factories</option></select><Icon className="chevron">expand_more</Icon></div></label>
          {geographyReady && <>
            <label><span>Tea-growing region</span><div className="control-wrap"><Icon>map</Icon><select aria-label="Tea growing region" value={teaRegion} onChange={(e) => setTeaRegion(e.target.value)}><option value="">All verified regions</option>{regionInfo.tea_growing_regions.map((value) => <option value={value} key={value}>{value}</option>)}</select><Icon className="chevron">expand_more</Icon></div></label>
            <label><span>District</span><div className="control-wrap"><Icon>location_on</Icon><select aria-label="District" value={district} onChange={(e) => setDistrict(e.target.value)}><option value="">All verified districts</option>{regionInfo.districts.map((value) => <option value={value} key={value}>{value}</option>)}</select><Icon className="chevron">expand_more</Icon></div></label>
            <label><span>Elevation</span><div className="control-wrap"><Icon>landscape</Icon><select aria-label="Elevation" value={elevation} onChange={(e) => setElevation(e.target.value)}><option value="">All verified elevations</option>{regionInfo.elevation_categories.map((value) => <option value={value} key={value}>{value}</option>)}</select><Icon className="chevron">expand_more</Icon></div></label>
          </>}
          <button className="primary-button" type="submit" disabled={loading}>{loading ? <><span className="spinner" /> Comparing…</> : <>Compare factories <Icon>compare_arrows</Icon></>}</button>
        </form>
        {!geographyReady && <p className="mapping-pending"><Icon>map</Icon>Regional filters are intentionally disabled until verified factory → district/region/elevation mappings are added.</p>}
        {geographyReady && <p className="mapping-ready"><Icon>verified</Icon>{regionInfo.verified_factory_count} verified factory mappings ({regionInfo.coverage_pct}% of eligible factories).</p>}
        {error && <div className="inline-error" role="alert"><Icon>error</Icon><span>{error}</span></div>}
      </section>
      {comparison && <section className="comparison-results">
        <div className="comparison-summary"><div><span>Prediction month</span><strong>{formatMonth(comparison.prediction_month)}</strong></div><div><span>Quantity used</span><strong>{money.format(comparison.expected_leaf_kg)} kg</strong></div><div><span>Eligible comparisons</span><strong>{comparison.eligible_result_count}</strong></div></div>
        <article className="panel comparison-table-card"><div className="panel-title"><h2>Highest predicted Reasonable Price alternatives</h2><Icon>leaderboard</Icon></div><div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Rank</th><th>Factory</th><th>Region</th><th>Predicted price</th><th>Estimated gross earnings</th><th>Reliability</th><th></th></tr></thead><tbody>{comparison.results.map((item) => <tr key={item.factory}><td><span className="rank-pill">#{item.price_rank}</span></td><td><strong>{item.factory_name}</strong><small>{item.factory}</small></td><td><strong>{item.tea_growing_region || "Not mapped"}</strong><small>{item.district || item.elevation_category || "—"}</small></td><td><strong>LKR {money.format(item.predicted_reasonable_price)}</strong><small>/ kg</small></td><td><strong>LKR {money.format(item.estimated_gross_earnings_lkr)}</strong><small>{money.format(item.expected_leaf_kg)} kg</small></td><td><span className={`reliability ${item.reliability.toLowerCase()}`}>{item.reliability}</span></td><td><button className="table-action" type="button" onClick={() => onOpenFactory(item.factory, comparison.prediction_month, comparison.expected_leaf_kg)}>View forecast</button></td></tr>)}</tbody></table></div><p className="comparison-note"><Icon>info</Icon>{comparison.decision_support_note}</p></article>
      </section>}
    </main>
  );
}

const susQuestions = [
  "I think that I would like to use this system frequently.",
  "I found the system unnecessarily complex.",
  "I thought the system was easy to use.",
  "I think that I would need the support of a technical person to use this system.",
  "I found the various functions in this system were well integrated.",
  "I thought there was too much inconsistency in this system.",
  "I would imagine that most people would learn to use this system very quickly.",
  "I found the system very cumbersome to use.",
  "I felt very confident using the system.",
  "I needed to learn a lot of things before I could get going with this system.",
];

function RatingSelect({ label, value, onChange }) {
  return <label className="evaluation-rating"><span>{label}</span><select value={value} onChange={(e) => onChange(Number(e.target.value))} required><option value="">Select</option>{[1,2,3,4,5].map((n) => <option value={n} key={n}>{n}</option>)}</select></label>;
}

function ResearchEvaluation() {
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [role, setRole] = useState("");
  const [consent, setConsent] = useState(false);
  const [tasks, setTasks] = useState([false, false, false, false, false]);
  const [sus, setSus] = useState(Array(10).fill(""));
  const [ratings, setRatings] = useState({ price: "", earnings: "", uncertainty: "", usefulness: "", trust: "" });
  const [comments, setComments] = useState("");

  useEffect(() => {
    apiRequest("/evaluation/status").then(setStatus).catch((err) => setError(err.message));
  }, []);

  function updateTask(index, value) {
    setTasks((current) => current.map((item, i) => i === index ? value : item));
  }
  function updateSus(index, value) {
    setSus((current) => current.map((item, i) => i === index ? value : item));
  }

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true); setError(""); setMessage("");
    try {
      const body = {
        role, consent,
        ...Object.fromEntries(tasks.map((value, i) => [`task${i + 1}_success`, value])),
        ...Object.fromEntries(sus.map((value, i) => [`sus_q${i + 1}`, Number(value)])),
        price_clarity_1to5: Number(ratings.price),
        earnings_clarity_1to5: Number(ratings.earnings),
        uncertainty_clarity_1to5: Number(ratings.uncertainty),
        usefulness_1to5: Number(ratings.usefulness),
        trust_appropriateness_1to5: Number(ratings.trust),
        comments,
      };
      const result = await apiRequest("/evaluation/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setMessage(`Response recorded as ${result.participant_code}. SUS score: ${result.sus_score}.`);
      setComments("");
    } catch (err) { setError(err.message); }
    finally { setSubmitting(false); }
  }

  const enabled = Boolean(status?.collection_enabled);
  return <main className="page evaluation-page">
    <section className="evaluation-hero"><div><p className="eyebrow">Research evaluation</p><h1>Evaluate the decision-support system with real participants.</h1><p>This form collects task completion, SUS usability ratings, clarity, usefulness and appropriately calibrated trust. It intentionally avoids names, emails, phone numbers and other unnecessary identifiers.</p></div><div className={`evaluation-status ${enabled ? "enabled" : "disabled"}`}><Icon>{enabled ? "verified_user" : "lock"}</Icon><strong>{enabled ? "Collection enabled" : "Collection disabled"}</strong><span>{enabled ? `${status?.response_count || 0} responses recorded` : "Enable only after required ethics/approval"}</span></div></section>
    {!enabled && <div className="alert research-alert"><Icon>info</Icon><div><strong>Research integrity safeguard</strong><span>Set <code>ENABLE_EVALUATION_COLLECTION=true</code> only after the required university ethics/approval process. No synthetic participant results are created.</span></div></div>}
    <form className="evaluation-form panel" onSubmit={submit}>
      <div className="panel-title"><h2>Participant evaluation</h2><Icon>assignment</Icon></div>
      <label><span>Participant role</span><input type="text" value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. tea smallholder / researcher / factory stakeholder" required disabled={!enabled} /></label>
      <fieldset><legend>Task completion</legend>{tasks.map((value, index) => <label className="task-check" key={index}><input type="checkbox" checked={value} onChange={(e) => updateTask(index, e.target.checked)} disabled={!enabled} /><span>Task {index + 1} completed successfully</span></label>)}</fieldset>
      <fieldset><legend>System Usability Scale · 1 strongly disagree → 5 strongly agree</legend><div className="sus-grid">{susQuestions.map((question, index) => <RatingSelect key={question} label={`${index + 1}. ${question}`} value={sus[index]} onChange={(value) => updateSus(index, value)} />)}</div></fieldset>
      <fieldset><legend>Research-specific ratings · 1 low → 5 high</legend><div className="rating-grid"><RatingSelect label="Price forecast clarity" value={ratings.price} onChange={(value) => setRatings({...ratings, price:value})} /><RatingSelect label="Gross-earnings clarity" value={ratings.earnings} onChange={(value) => setRatings({...ratings, earnings:value})} /><RatingSelect label="Uncertainty / range clarity" value={ratings.uncertainty} onChange={(value) => setRatings({...ratings, uncertainty:value})} /><RatingSelect label="Usefulness for planning" value={ratings.usefulness} onChange={(value) => setRatings({...ratings, usefulness:value})} /><RatingSelect label="Trust appropriateness" value={ratings.trust} onChange={(value) => setRatings({...ratings, trust:value})} /></div></fieldset>
      <label><span>Optional comments</span><textarea value={comments} onChange={(e) => setComments(e.target.value)} maxLength="2000" rows="4" disabled={!enabled} /></label>
      <label className="consent-check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required disabled={!enabled} /><span>I consent to this anonymized research evaluation under the approved study process.</span></label>
      <button className="primary-button" type="submit" disabled={!enabled || submitting}>{submitting ? "Submitting…" : "Submit evaluation"}</button>
      {message && <div className="inline-success"><Icon>check_circle</Icon><span>{message}</span></div>}
      {error && <div className="inline-error" role="alert"><Icon>error</Icon><span>{error}</span></div>}
    </form>
  </main>;
}

const pipelineInputs = [
  ["factory", "Factory history", "Auction prices and sale volumes"],
  ["eco", "Production", "Green-leaf intake and output"],
  ["partly_cloudy_day", "Weather", "Rainfall, temperature and humidity"],
  ["currency_exchange", "Exchange rates", "LKR and global price signals"],
  ["public", "Export data", "Demand, values and destinations"],
];

function About({ health, onPredict }) {
  return (
    <main className="page about-page">
      <section className="about-hero">
        <div className="about-hero-copy"><p className="eyebrow">Transparent by design</p><h1>Understanding the prediction engine</h1><p>TeaReasonable AI uses CatBoost to combine agricultural and economic signals into a guarded one-month-ahead price forecast.</p></div>
        <div className="about-cup-visual" aria-hidden="true"><span className="cup-halo" /><img src="/images/tea-cup.png" alt="" width="768" height="512" loading="lazy" decoding="async" /><span className="steam steam-one" /><span className="steam steam-two" /></div>
      </section>
      <section className="pipeline-section"><div className="section-title"><Icon>schema</Icon><div><p className="eyebrow">From data to decision</p><h2>Data pipeline</h2></div></div><div className="pipeline-card panel"><div className="input-grid">{pipelineInputs.map(([icon, title, copy]) => <div className="input-card" key={title}><span><Icon>{icon}</Icon></span><div><strong>{title}</strong><p>{copy}</p></div></div>)}</div><div className="pipeline-arrow"><Icon>arrow_forward</Icon></div><div className="model-card"><Icon>model_training</Icon><h3>{health?.model?.replace("_", " ") || "CatBoost model"}</h3><p>Gradient-boosted decision trees capture non-linear seasonal patterns and categorical factory effects.</p><div><Icon>monitoring</Icon><span>Output</span><strong>Predicted price in LKR / kg</strong></div></div></div></section>
      <section className="method-grid"><article><div className="section-title compact"><Icon>verified_user</Icon><div><p className="eyebrow">Prediction safeguards</p><h2>Quality checks first</h2></div></div><p>The API refuses a forecast when the preceding price is unreliable, history is insufficient, or feature coverage drops below the configured threshold.</p><div className="guardrail-list"><div><Icon>history</Icon><span><b>36 months</b> minimum reliable history</span></div><div><Icon>data_check</Icon><span><b>60%</b> minimum feature completeness</span></div><div><Icon>event_repeat</Icon><span><b>1 month</b> fixed forecast horizon</span></div></div></article><article><div className="section-title compact"><Icon>analytics</Icon><div><p className="eyebrow">Result interpretation</p><h2>Decision support</h2></div></div><p>Every result pairs the central estimate with an approximate 90% range, completeness score, history depth, and data-quality notes.</p><div className="decision-note"><Icon>info</Icon><p>Forecasts support planning; they are not financial guarantees. Extreme weather and market shocks may move prices outside the displayed range.</p></div></article></section>
      <section className="about-cta"><div><p className="eyebrow">Ready to explore?</p><h2>Generate a forecast from verified factory data.</h2></div><button className="primary-button" type="button" onClick={onPredict}>Start a prediction <Icon>arrow_forward</Icon></button></section>
    </main>
  );
}

function getPageFromHash() {
  const value = window.location.hash.replace("#", "");
  return ["dashboard", "results", "compare", "evaluation", "about"].includes(value) ? value : "dashboard";
}

function App() {
  const [page, setPage] = useState(getPageFromHash);
  const [health, setHealth] = useState(null);
  const [regionInfo, setRegionInfo] = useState(null);
  const [factories, setFactories] = useState([]);
  const [factory, setFactory] = useState("");
  const [targetMonth, setTargetMonth] = useState("2026-01");
  const [expectedLeafKg, setExpectedLeafKg] = useState("1250");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [predictionError, setPredictionError] = useState("");
  const [prediction, setPrediction] = useState(loadPrediction);

  useEffect(() => {
    const handleHash = () => setPage(getPageFromHash());
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const [healthData, factoryData, regionsData] = await Promise.all([apiRequest("/health"), apiRequest("/factories"), apiRequest("/regions")]);
        if (!active) return;
        setHealth(healthData);
        setRegionInfo(regionsData);
        setFactories(factoryData);
        const preferred = factoryData.find((item) => String(item.Factory) === "BF0143") || factoryData[0];
        if (preferred) {
          setFactory(String(preferred.Factory));
          if (preferred.latest_prediction_month) setTargetMonth(preferred.latest_prediction_month.slice(0, 7));
        }
      } catch (error) {
        if (active) setConnectionError(`${error.message} Confirm FastAPI is running on ${API_BASE_URL}.`);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => { active = false; };
  }, []);

  function navigate(target) {
    if (target === "compare") {
      window.location.hash = "compare";
      setPage("compare");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    if (target === "predict") {
      window.location.hash = "dashboard";
      setPage("dashboard");
      window.setTimeout(() => document.getElementById("prediction-form")?.scrollIntoView({ behavior: "smooth" }), 80);
      return;
    }
    window.location.hash = target;
    setPage(target);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!factory || !targetMonth || !expectedLeafKg) return;
    const [year, month] = targetMonth.split("-").map(Number);
    setSubmitting(true);
    setPredictionError("");
    try {
      const result = await apiRequest("/estimate-earnings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ factory, year, month, expected_leaf_kg: Number(expectedLeafKg) }) });
      setPrediction(result);
      savePrediction(result);
      navigate("results");
    } catch (error) {
      setPredictionError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  function openFactoryFromComparison(factoryCode, predictionMonth, quantity) {
    setFactory(String(factoryCode));
    setTargetMonth(String(predictionMonth).slice(0, 7));
    setExpectedLeafKg(String(quantity));
    navigate("predict");
  }

  const content = useMemo(() => {
    if (page === "results") return <Results prediction={prediction} onNewPrediction={() => navigate("predict")} />;
    if (page === "compare") return <CompareFactories defaultMonth={targetMonth} defaultQuantity={expectedLeafKg} onOpenFactory={openFactoryFromComparison} regionInfo={regionInfo} />;
    if (page === "evaluation") return <ResearchEvaluation />;
    if (page === "about") return <About health={health} onPredict={() => navigate("predict")} />;
    return <Dashboard health={health} factories={factories} factory={factory} setFactory={setFactory} targetMonth={targetMonth} setTargetMonth={setTargetMonth} expectedLeafKg={expectedLeafKg} setExpectedLeafKg={setExpectedLeafKg} loading={loading} submitting={submitting} connectionError={connectionError} predictionError={predictionError} onSubmit={handleSubmit} onCompare={() => navigate("compare")} />;
  }, [page, prediction, health, regionInfo, factories, factory, targetMonth, expectedLeafKg, loading, submitting, connectionError, predictionError]);

  return <div className="app-shell"><Header page={page} health={health} loading={loading} onNavigate={navigate} />{content}<Footer health={health} onNavigate={navigate} /></div>;
}

export default App;
