# 3D Spike Map: Domestic Migration by US County (2024)
# Using rayshader for beautiful 3D visualization

library(rayshader)
library(sf)
library(ggplot2)
library(dplyr)
library(viridis)

# ============================================================================
# CONFIGURATION
# ============================================================================

BLUE <- "#0BB4FF"
RED <- "#F4743B"
CREAM <- "#DADFCE"
BG_CREAM <- "#F6F7F3"

DATA_LAKE <- "/Users/azizsunderji/Dropbox/Home Economics/Data"
REFERENCE <- "/Users/azizsunderji/Dropbox/Home Economics/Reference"
OUTPUT_DIR <- "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"

EXCLUDE_STATES <- c('02', '15', '60', '66', '69', '72', '78')

ALBERS <- '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# ============================================================================
# LOAD DATA
# ============================================================================

cat("Loading data...\n")

# Load population data
pop_df <- arrow::read_parquet(file.path(DATA_LAKE, "PopulationEstimates/county_v2024.parquet"))

pop_df <- pop_df %>%
  filter(SUMLEV == 50) %>%
  mutate(
    STATEFP = sprintf("%02d", STATE),
    COUNTYFP = sprintf("%03d", COUNTY),
    GEOID = paste0(STATEFP, COUNTYFP)
  ) %>%
  select(GEOID, STATEFP, CTYNAME, STNAME,
         population = POPESTIMATE2024,
         domestic_migration = DOMESTICMIG2024)

cat("Loaded", nrow(pop_df), "counties\n")

# Load county shapefile
counties <- st_read(file.path(REFERENCE, "Shapefiles/cb_2023_county/cb_2023_us_county_5m.shp"), quiet = TRUE)

# Filter and merge
counties <- counties %>%
  filter(!STATEFP %in% EXCLUDE_STATES) %>%
  left_join(pop_df, by = c("GEOID", "STATEFP")) %>%
  filter(!is.na(domestic_migration)) %>%
  st_transform(ALBERS)

cat("Counties with data:", nrow(counties), "\n")

# Load state boundaries for base map
states <- st_read(file.path(REFERENCE, "Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp"), quiet = TRUE)
states <- states %>%
  filter(!STATEFP %in% EXCLUDE_STATES) %>%
  st_transform(ALBERS)

# ============================================================================
# CREATE GGPLOT CHOROPLETH
# ============================================================================

cat("Creating choropleth map...\n")

# Create a choropleth that rayshader can extrude
# The fill color intensity will become the extrusion height

# Normalize migration to 0-1 scale for fill
max_abs <- quantile(abs(counties$domestic_migration), 0.98, na.rm = TRUE)

counties <- counties %>%
  mutate(
    migration_normalized = domestic_migration / max_abs,
    migration_capped = pmin(pmax(migration_normalized, -1), 1),
    # Convert to a single scale for fill - positive high, negative low
    fill_value = (migration_capped + 1) / 2  # 0 to 1 scale
  )

# Create plot - use fill aesthetic for extrusion
p <- ggplot() +
  geom_sf(data = states, fill = CREAM, color = "white", linewidth = 0.2) +
  geom_sf(data = counties, aes(fill = domestic_migration), color = NA) +
  scale_fill_gradient2(
    low = RED,
    mid = CREAM,
    high = BLUE,
    midpoint = 0,
    limits = c(-max_abs, max_abs),
    oob = scales::squish
  ) +
  theme_void() +
  theme(
    legend.position = "none",
    plot.background = element_rect(fill = BG_CREAM, color = NA),
    panel.background = element_rect(fill = BG_CREAM, color = NA)
  ) +
  coord_sf()

cat("Rendering with rayshader...\n")

# ============================================================================
# RENDER WITH RAYSHADER
# ============================================================================

# Convert ggplot to 3D
# plot_gg extrudes based on fill color intensity
plot_gg(
  p,
  width = 9,
  height = 7,
  scale = 350,           # Increased extrusion
  raytrace = TRUE,
  multicore = TRUE,
  windowsize = c(2700, 2100),
  zoom = 0.55,           # Slightly zoomed out
  theta = -25,           # Rotated more
  phi = 45,              # Higher angle
  background = BG_CREAM,
  shadow_intensity = 0.6,
  sunangle = 315         # Sun from northwest for better shadows
)

# Save high-quality render
output_path <- file.path(OUTPUT_DIR, "domestic_migration_rayshader.png")

render_snapshot(
  filename = output_path,
  clear = TRUE
)

cat("\nSaved:", output_path, "\n")
cat("Done!\n")
