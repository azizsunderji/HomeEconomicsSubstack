# High-Rise Housing Growth 2013-2023 - TOP 30 METROS
# Blue to yellow gradient, no background block, overhead view

library(rayshader)
library(sf)
library(ggplot2)
library(dplyr)

# ============================================================================
# CONFIGURATION
# ============================================================================

BLUE <- "#0BB4FF"
YELLOW <- "#FEC439"
CREAM <- "#DADFCE"
BG_CREAM <- "#F6F7F3"

OUTPUT_DIR <- "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"
DATA_DIR <- "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/data"
REFERENCE <- "/Users/azizsunderji/Dropbox/Home Economics/Reference"

EXCLUDE_STATES <- c('02', '15', '60', '66', '69', '72', '78')
ALBERS <- '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# ============================================================================
# LOAD DATA
# ============================================================================

cat("Loading data...\n")

hr_data <- read.csv(file.path(DATA_DIR, "highrise_growth_all_metros.csv"))
cat("All metros loaded:", nrow(hr_data), "\n")

# TOP 30 ONLY
hr_data <- hr_data %>%
  arrange(desc(growth_10yr)) %>%
  head(30)
cat("Top 30 metros selected\n")

# Convert to sf and project
hr_sf <- st_as_sf(hr_data, coords = c("lon", "lat"), crs = 4326)
hr_sf <- st_transform(hr_sf, ALBERS)

# Load state boundaries
states <- st_read(file.path(REFERENCE, "Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp"), quiet = TRUE)
states <- states %>%
  filter(!STATEFP %in% EXCLUDE_STATES) %>%
  st_transform(ALBERS)

cat("States:", nrow(states), "\n")

# ============================================================================
# CREATE SPIKE POLYGONS
# ============================================================================

cat("Creating spike polygons...\n")

buffer_size <- 35000  # 35km radius - slightly larger for fewer metros

metro_circles <- hr_sf %>%
  st_buffer(buffer_size) %>%
  st_as_sf()

# SQRT scale for height differentiation
metro_circles$growth_sqrt <- sqrt(hr_data$growth_10yr)

cat("Created", nrow(metro_circles), "spike polygons\n")
cat("Growth range:", min(hr_data$growth_10yr), "to", max(hr_data$growth_10yr), "\n")

# ============================================================================
# CREATE GGPLOT - BLUE TO YELLOW GRADIENT
# ============================================================================

cat("Creating plot...\n")

p <- ggplot() +
  geom_sf(data = states, fill = CREAM, color = "white", linewidth = 0.3) +
  geom_sf(
    data = metro_circles,
    aes(fill = growth_sqrt),
    color = NA
  ) +
  # Blue to Yellow gradient based on growth
  scale_fill_gradient(
    low = BLUE,
    high = YELLOW
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

plot_gg(
  p,
  width = 9,
  height = 7,
  scale = 400,
  raytrace = TRUE,
  multicore = TRUE,
  windowsize = c(2700, 2100),
  zoom = 0.55,
  theta = -20,
  phi = 55,                  # More overhead view
  background = BG_CREAM,
  shadow_intensity = 0.08,   # Very light shadows
  sunangle = 315,
  soliddepth = -20           # Push base down so spikes start above surface
)

output_path <- file.path(OUTPUT_DIR, "highrise_growth_top30.png")
render_snapshot(filename = output_path, clear = TRUE)

cat("\nSaved:", output_path, "\n")
cat("Done!\n")
