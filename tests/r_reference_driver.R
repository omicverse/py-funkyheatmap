#!/usr/bin/env Rscript
# Generate the canonical R fixture outputs used by py-funkyheatmap parity.
#
# Writes:
#   data/r_basic.csv           - the input data frame used for the basic example
#   data/r_basic_funkyrect.csv - per-cell funkyrect geometry from R
#   data/r_basic.png           - the rendered R figure (visual reference)

suppressPackageStartupMessages({
  library(funkyheatmap)
  library(tibble)
  library(dplyr)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
out_dir <- if (length(args) >= 1) args[[1]] else "data"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

set.seed(0)
n <- 8
data <- tibble(
  id = paste0("m", 0:(n - 1)),
  name = paste("Method", 0:(n - 1)),
  metric_a = runif(n),
  metric_b = runif(n),
  metric_c = runif(n)
)

# Fixed example so Python and R use byte-identical input
write.csv(data, file.path(out_dir, "r_basic.csv"), row.names = FALSE)

column_info <- tribble(
  ~id,        ~name,    ~geom,
  "name",     "Method", "text",
  "metric_a", "A",      "funkyrect",
  "metric_b", "B",      "funkyrect",
  "metric_c", "C",      "circle"
)

g <- funky_heatmap(data, column_info = column_info, add_abc = FALSE)

# Internal positions — we recompute and dump them so Python can diff
column_info_v <- verify_column_info(column_info, data)
row_info_v    <- verify_row_info(NULL, data)
palettes_v    <- verify_palettes(NULL, column_info_v, data)
position_args <- position_arguments()

geom_positions <- funkyheatmap:::calculate_geom_positions(
  data, column_info_v, row_info_v,
  column_groups = NULL, row_groups = NULL,
  palettes = palettes_v,
  position_args = position_args,
  scale_column = TRUE, add_abc = FALSE
)

write.csv(
  geom_positions$funkyrect_data %>%
    mutate(across(where(is.numeric), ~ round(.x, 6))),
  file.path(out_dir, "r_basic_funkyrect.csv"),
  row.names = FALSE
)
write.csv(
  geom_positions$circle_data %>%
    mutate(across(where(is.numeric), ~ round(.x, 6))),
  file.path(out_dir, "r_basic_circle.csv"),
  row.names = FALSE
)

ggsave(file.path(out_dir, "r_basic.png"), g, width = g$width, height = g$height, dpi = 150)
cat("R reference written to:", out_dir, "\n")
