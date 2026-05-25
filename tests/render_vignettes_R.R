#!/usr/bin/env Rscript
# Render the R-side reference for both vignettes so the Python notebooks can
# show a side-by-side. The Rmd files do this with knitr — we re-execute the
# essential figure chunks here from data already shipped in funkyheatmap.

suppressPackageStartupMessages({
  library(funkyheatmap)
  library(dplyr)
  library(tibble)
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
out_dir <- if (length(args) >= 1) args[[1]] else "data/vignettes"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# ---- scIB --------------------------------------------------------------
data("scib_summary")

label_top_3 <- function(scores, ...) {
  ranks <- rank(scores, ...)
  ifelse(ranks <= 3, as.character(ranks), "")
}

scib_summary_plot <- scib_summary |>
  mutate(id = as.character(seq_len(nrow(scib_summary)))) |>
  mutate(
    scaling  = factor(scaling, levels = c("Unscaled", "Scaled"), labels = c("-", "+")),
    features = factor(features, levels = c("Full", "HVG"), labels = c("FULL", "HVG"))
  ) |>
  mutate(
    output_img = dplyr::case_match(
      output,
      "Features"  ~ "images/matrix.png",
      "Embedding" ~ "images/embedding.png",
      "Graph"     ~ "images/graph.png"
    )
  ) |>
  mutate(
    label_pancreas             = label_top_3(rank_pancreas),
    label_lung_atlas           = label_top_3(rank_lung_atlas),
    label_immune_cell_hum      = label_top_3(rank_immune_cell_hum),
    label_immune_cell_hum_mou  = label_top_3(rank_immune_cell_hum_mou),
    label_mouse_brain          = label_top_3(rank_mouse_brain),
    label_simulations_1_1      = label_top_3(rank_simulations_1_1),
    label_simulations_2        = label_top_3(rank_simulations_2),
    package_label              = label_top_3(package_rank, ties.method = "min"),
    paper_label                = label_top_3(paper_rank, ties.method = "min"),
    time_label                 = label_top_3(time_rank, ties.method = "min"),
    memory_label               = label_top_3(memory_rank, ties.method = "min")
  ) |>
  mutate_at(
    c("rank_pancreas","rank_lung_atlas","rank_immune_cell_hum","rank_immune_cell_hum_mou",
      "rank_mouse_brain","rank_simulations_1_1","rank_simulations_2",
      "package_rank","paper_rank","time_rank","memory_rank"),
    function(x) scale_minmax(-x)
  ) |>
  as.data.frame()

# write the prepared frame so Python can use the *same* preprocessed data
write.csv(scib_summary_plot, file.path(out_dir, "scib_summary_plot.csv"), row.names = FALSE)

column_info <- tribble(
  ~id, ~id_color, ~name, ~geom, ~group, ~options,
  "id", NA, "Rank", "text", "Method", list(hjust = 0),
  "method", NA, "Method", "text", "Method", list(hjust = 0, width = 5),
  "output_img", NA, "Output", "image", "Method", list(),
  "features", "features", "Features", "text", "Method", list(palette = "features", width = 2),
  "scaling", NA, "Scaling", "text", "Method", list(fontface = "bold"),
  "overall_pancreas", "rank_pancreas", "Pancreas", "bar", "RNA", list(palette = "blues", width = 1.5, draw_outline = FALSE),
  "label_pancreas", NA, NA, "text", "RNA", list(hjust = .1, overlay = TRUE),
  "overall_lung_atlas", "rank_lung_atlas", "Lung", "bar", "RNA", list(palette = "blues", width = 1.5, draw_outline = FALSE),
  "label_lung_atlas", NA, NA, "text", "RNA", list(hjust = .1, overlay = TRUE),
  "overall_immune_cell_hum", "rank_immune_cell_hum", "Immune (human)", "bar", "RNA", list(palette = "blues", width = 1.5, draw_outline = FALSE),
  "label_immune_cell_hum", NA, NA, "text", "RNA", list(hjust = .1, overlay = TRUE),
  "overall_immune_cell_hum_mou", "rank_immune_cell_hum_mou", "Immune (human/mouse)", "bar", "RNA", list(palette = "blues", width = 1.5, draw_outline = FALSE),
  "label_immune_cell_hum_mou", NA, NA, "text", "RNA", list(hjust = .1, overlay = TRUE),
  "overall_mouse_brain", "rank_mouse_brain", "Mouse brain", "bar", "RNA", list(palette = "blues", width = 1.5, draw_outline = FALSE),
  "label_mouse_brain", NA, NA, "text", "RNA", list(hjust = .1, overlay = TRUE),
  "overall_simulations_1_1", "rank_simulations_1_1", "Sim 1", "bar", "Simulations", list(palette = "greens", width = 1.5, draw_outline = FALSE),
  "label_simulations_1_1", NA, NA, "text", "Simulations", list(hjust = .1, overlay = TRUE),
  "overall_simulations_2", "rank_simulations_2", "Sim 2", "bar", "Simulations", list(palette = "greens", width = 1.5, draw_outline = FALSE),
  "label_simulations_2", NA, NA, "text", "Simulations", list(hjust = .1, overlay = TRUE),
  "package_score", "package_rank", "Package", "bar", "Usability", list(palette = "oranges", width = 1.5, draw_outline = FALSE),
  "package_label", NA, NA, "text", "Usability", list(hjust = .1, overlay = TRUE),
  "paper_score", "paper_rank", "Paper", "bar", "Usability", list(palette = "oranges", width = 1.5, draw_outline = FALSE),
  "paper_label", NA, NA, "text", "Usability", list(hjust = .1, overlay = TRUE),
  "time_score", "time_rank", "Time", "bar", "Scalability", list(palette = "greys", width = 1.5, draw_outline = FALSE),
  "time_label", NA, NA, "text", "Scalability", list(hjust = .1, overlay = TRUE),
  "memory_score", "memory_rank", "Memory", "bar", "Scalability", list(palette = "greys", width = 1.5, draw_outline = FALSE),
  "memory_label", NA, NA, "text", "Scalability", list(hjust = .1, overlay = TRUE)
)

column_groups <- tribble(
  ~group, ~palette, ~level1,
  "Method", "black", "Method",
  "RNA", "blues", "RNA",
  "Simulations", "greens", "Simulations",
  "Usability", "oranges", "Usability",
  "Scalability", "greys", "Scalability"
)

row_info <- data.frame(id = scib_summary_plot$id, group = NA_character_)

palettes <- list(
  features = c(FULL = "#4c4c4c", HVG = "#006300"),
  blues = "Blues",
  greens = "Greens",
  oranges = rev(RColorBrewer::brewer.pal(9, "Oranges")),
  greys = "Greys",
  black = c("black", "black")
)

legends <- list(
  list(title = "Scaling", geom = "text", values = c("Scaled","Unscaled"), labels = c("+","-"), label_width = .5),
  list(title = "RNA rank",         palette = "blues",   geom = "rect", labels = c("20"," ","10"," ","1"), size = c(1,1,1,1,1)),
  list(title = "Simulations rank", palette = "greens",  geom = "rect", labels = c("20"," ","10"," ","1"), size = c(1,1,1,1,1)),
  list(title = "Usability rank",   palette = "oranges", geom = "rect", labels = c("20"," ","10"," ","1"), size = c(1,1,1,1,1)),
  list(title = "Scalability rank", palette = "greys",   geom = "rect", labels = c("20"," ","10"," ","1"), size = c(1,1,1,1,1))
)

g <- funky_heatmap(
  data         = scib_summary_plot,
  column_info  = column_info,
  column_groups = column_groups,
  row_info     = row_info,
  palettes     = palettes,
  legends      = legends,
  position_args = position_arguments(col_annot_offset = 4),
  scale_column  = FALSE
)
ggsave(file.path(out_dir, "scib_R.png"), g, width = g$width, height = g$height, dpi = 150, limitsize = FALSE)
cat("wrote scib_R.png (", round(g$width,1), "x", round(g$height,1), ")\n")

# ---- dynbenchmark ------------------------------------------------------
data("dynbenchmark_data")
g <- funky_heatmap(
  data         = dynbenchmark_data$data,
  column_info  = dynbenchmark_data$column_info,
  column_groups = dynbenchmark_data$column_groups,
  row_info     = dynbenchmark_data$row_info,
  row_groups   = dynbenchmark_data$row_groups,
  palettes     = dynbenchmark_data$palettes,
  col_annot_offset = 3.2
)
ggsave(file.path(out_dir, "dynbenchmark_R.png"), g, width = g$width, height = g$height, dpi = 150, limitsize = FALSE)
cat("wrote dynbenchmark_R.png (", round(g$width,1), "x", round(g$height,1), ")\n")
