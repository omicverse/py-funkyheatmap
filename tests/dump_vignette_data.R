#!/usr/bin/env Rscript
# Dump the canonical scIB + dynbenchmark fixture data so the Python vignettes
# can read byte-identical inputs.
#
# Outputs (under `data/vignettes/`):
#   scib_summary.csv
#   dynbenchmark_data.csv         (main data table)
#   dynbenchmark_column_info.json (list-column-safe)
#   dynbenchmark_column_groups.csv
#   dynbenchmark_row_info.csv
#   dynbenchmark_row_groups.csv
#   dynbenchmark_palettes.json

suppressPackageStartupMessages({
  library(funkyheatmap)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
out_dir <- if (length(args) >= 1) args[[1]] else "data/vignettes"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

data("scib_summary")
data("dynbenchmark_data")

# ---- scIB --------------------------------------------------------------
write.csv(as.data.frame(scib_summary), file.path(out_dir, "scib_summary.csv"), row.names = FALSE)

# ---- dynbenchmark ------------------------------------------------------
data <- dynbenchmark_data$data

sanitize_for_json <- function(x) {
  if (is.null(x)) return(NULL)
  if (is.function(x) || is.environment(x) || is.language(x) && !is.name(x)) return(NULL)
  if (is.name(x) || is.symbol(x) || is.factor(x)) return(as.character(x))
  if (is.list(x)) return(lapply(x, sanitize_for_json))
  x
}

# columns whose values are dicts (named numeric vectors) get serialised to JSON strings
list_cols <- sapply(data, is.list)
for (col in names(data)[list_cols]) {
  data[[col]] <- sapply(data[[col]], function(x) {
    if (is.null(x) || length(x) == 0) return("{}")
    tryCatch({
      jsonlite::toJSON(sanitize_for_json(x), auto_unbox = TRUE, null = "null", na = "null")
    }, error = function(e) "{}")
  })
}
# any remaining factor columns -> character
data[] <- lapply(data, function(col) if (is.factor(col)) as.character(col) else col)
write.csv(data, file.path(out_dir, "dynbenchmark_data.csv"), row.names = FALSE)
# remember which columns were lists so Python can deserialize
writeLines(names(which(list_cols)), file.path(out_dir, "dynbenchmark_data_list_cols.txt"))

# column_info: the `options` column contains lists which must survive
ci <- dynbenchmark_data$column_info

# coerce R names / symbols / factors to plain character before JSON
sanitize <- function(x) {
  if (is.list(x)) {
    lapply(x, sanitize)
  } else if (is.name(x) || is.symbol(x) || is.factor(x)) {
    as.character(x)
  } else {
    x
  }
}

# convert the options list column to JSON strings per row
ci$options <- sapply(ci$options, function(x) {
  if (is.null(x) || length(x) == 0) {
    "{}"
  } else {
    jsonlite::toJSON(sanitize(as.list(x)), auto_unbox = TRUE, null = "null", na = "null")
  }
})
# remaining columns are all atomic; coerce any remaining factors to chr for safety
ci[] <- lapply(ci, function(col) if (is.factor(col)) as.character(col) else col)
write.csv(ci, file.path(out_dir, "dynbenchmark_column_info.csv"), row.names = FALSE)

cg <- dynbenchmark_data$column_groups
write.csv(cg, file.path(out_dir, "dynbenchmark_column_groups.csv"), row.names = FALSE)

ri <- dynbenchmark_data$row_info
write.csv(ri, file.path(out_dir, "dynbenchmark_row_info.csv"), row.names = FALSE)

rg <- dynbenchmark_data$row_groups
write.csv(rg, file.path(out_dir, "dynbenchmark_row_groups.csv"), row.names = FALSE)

palettes <- dynbenchmark_data$palettes
# tibble of palette / colours -> a JSON list of {palette, colours} where each
# colours entry preserves names so the Python side can build a category map.
pal_records <- lapply(seq_len(nrow(palettes)), function(i) {
  cols <- palettes$colours[[i]]
  if (!is.null(names(cols)) && any(nzchar(names(cols)))) {
    # named vector -> {name: hex}
    colours <- as.list(cols)
  } else {
    colours <- unname(as.character(cols))
  }
  list(palette = palettes$palette[[i]], colours = colours)
})
write_json(pal_records, file.path(out_dir, "dynbenchmark_palettes.json"),
           pretty = TRUE, auto_unbox = TRUE)

cat("Wrote vignette fixtures to:", out_dir, "\n")
cat("scib_summary rows:", nrow(scib_summary), "cols:", ncol(scib_summary), "\n")
cat("dynbenchmark data rows:", nrow(data), "cols:", ncol(data), "\n")
cat("dynbenchmark list cols:", names(which(list_cols)), "\n")
