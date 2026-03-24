// Chart registry — project_page.html loads this via <script>
var CHARTS_DATA = [
  {
    id: "ftb-longrun",
    title: "FTB long-run (3 series)",
    subtitle: "Ownership (PSID), Marriage (CPS/ACS), Headship (CPS). MS-2 method + ACS direct post-2008.",
    file: "ftb_longrun.html",
    height: 987,
    tags: ["ownership", "marriage", "headship", "main"],
    date: "2026-03-20"
  },
  {
    id: "ftb-all-sources",
    title: "FTB all sources (6 series)",
    subtitle: "PSID, AHS, CPS ownership + Census MS-2, CPS marriage, CPS headship. Original 6-series version.",
    file: "ftb_all_sources.html",
    height: 987,
    tags: ["ownership", "marriage", "headship"],
    date: "2026-03-16"
  },
  {
    id: "ftb-ms2-vs-naive",
    title: "MS-2 vs naive method comparison",
    subtitle: "Two charts showing same data with MS-2 adjusted method vs raw 50% crossing.",
    file: "ftb_ms2_vs_naive.html",
    height: 1750,
    tags: ["methodology"],
    date: "2026-03-20"
  },
  {
    id: "milestones-priestley",
    title: "Priestley timeline (widening gaps)",
    subtitle: "Horizontal bars showing headship, marriage, ownership ages with gap labels. No population thickness.",
    file: "milestones_priestley_sankey.html",
    height: 1400,
    tags: ["milestones", "priestley"],
    date: "2026-03-20"
  },
  {
    id: "milestones-phases",
    title: "Priestley with population phases",
    subtitle: "4 colored phases with bar thickness = population share. Age on x-axis.",
    file: "milestones_phases.html",
    height: 987,
    tags: ["milestones", "priestley"],
    date: "2026-03-20"
  },
  {
    id: "milestones-combined",
    title: "Combined milestones (4 lines)",
    subtitle: "CPS headship, CPS marriage, PSID marriage, PSID ownership on one chart.",
    file: "milestones_combined.html",
    height: 987,
    tags: ["milestones", "line"],
    date: "2026-03-20"
  },
  {
    id: "psid-milestones",
    title: "PSID longitudinal milestones",
    subtitle: "All 3 milestones from PSID panel data. Marriage (retrospective), headship and ownership (tracked).",
    file: "psid_milestones.html",
    height: 850,
    tags: ["milestones", "psid"],
    date: "2026-03-20"
  },
  {
    id: "population-lifecycle",
    title: "Population lifecycle (stacked bar)",
    subtitle: "6-category stacked bar: children, adult dependents, unmarried renter/owner, married renter/owner.",
    file: "population_lifecycle.html",
    height: 750,
    tags: ["population"],
    date: "2026-03-20"
  },
  {
    id: "sankey-cohort",
    title: "Sankey prototype (born 1993)",
    subtitle: "True Sankey with d3-sankey. 4 states, 4 age columns, computed net flows.",
    file: "sankey_cohort.html",
    height: 700,
    tags: ["sankey", "cohort"],
    date: "2026-03-20"
  },
  {
    id: "sankey-3cohorts",
    title: "Sankey: Boomer vs Gen X vs Millennial",
    subtitle: "Three cohort Sankeys (born 1958, 1970, 1985) showing flows ages 18-40.",
    file: "sankey_3cohorts.html",
    height: 1600,
    tags: ["sankey", "cohort"],
    date: "2026-03-20"
  },
  {
    id: "sankey-age",
    title: "Stacked area by age (1976 vs 2025)",
    subtitle: "Population shares at each age. NOT a true Sankey despite the name.",
    file: "sankey_age.html",
    height: 1100,
    tags: ["population", "stacked"],
    date: "2026-03-20"
  },
  {
    id: "alluvial",
    title: "Alluvial (stacked area, smoothed)",
    subtitle: "Stacked area with annotations at peak transition ages. 1976 vs 2025.",
    file: "alluvial.html",
    height: 1100,
    tags: ["population", "stacked"],
    date: "2026-03-20"
  },
  {
    id: "ahs-ftb-age",
    title: "AHS FTB age (early version)",
    subtitle: "American Housing Survey first-time buyer age, 1985-2023.",
    file: "ahs_ftb_age.html",
    height: 600,
    tags: ["ownership", "ahs"],
    date: "2026-03-16"
  },
  {
    id: "cps-ftb-redfin",
    title: "CPS/Redfin FTB (early version)",
    subtitle: "CPS ASEC methodology matching Redfin's published numbers.",
    file: "cps_ftb_redfin.html",
    height: 600,
    tags: ["ownership", "cps"],
    date: "2026-03-19"
  },
];
charts = CHARTS_DATA;
