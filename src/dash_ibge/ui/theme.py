CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,600&display=swap');

html, body, [class*="css"] {
  font-family: "Source Sans 3", sans-serif;
}
.page-head h1 {
  font-family: "Source Serif 4", Georgia, serif;
  font-weight: 600;
  letter-spacing: -0.03em;
  margin-bottom: 0.15rem;
  color: #1c2834;
}
.page-head p {
  color: #5c6b73;
  margin-top: 0;
  font-size: 1.05rem;
}
div[data-testid="stMetric"] {
  background: #fffdf8;
  border: 1px solid #e0d8c8;
  border-radius: 14px;
  padding: 0.7rem 0.85rem;
}
div[data-testid="stMetricValue"] {
  font-variant-numeric: tabular-nums;
}
.note {
  color: #5c6b73;
  font-size: 0.92rem;
}
.answer {
  background: #fffdf8;
  border-left: 4px solid #0f6e56;
  border-radius: 0 12px 12px 0;
  padding: 0.9rem 1rem;
  white-space: pre-wrap;
}
footer {visibility: hidden;}
</style>
"""

COLORWAY = ["#0f6e56", "#c4552a", "#1f4e79", "#c4a35a", "#3d6b58", "#8c3a3a", "#5c6b73"]
