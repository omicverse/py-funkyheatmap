#!/usr/bin/env Rscript
# Render the FINAL figure of the getting-started vignette in R for parity.
suppressPackageStartupMessages({
  library(funkyheatmap); library(dplyr); library(tibble); library(purrr); library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
out_dir <- if (length(args) >= 1) args[[1]] else "data/vignettes"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

data("mtcars")
data <- mtcars %>% rownames_to_column("id") %>% arrange(desc(mpg)) %>% head(30)
data <- data[, c("id","qsec","mpg","wt","cyl","carb","disp","hp","vs","drat","am","gear")]

cinfo <- tibble(
  id = colnames(data),
  group = c(NA, "Performance", rep("Overall", 2), rep("Engine", 5), rep("Transmission", 3)),
  options = lapply(seq(12), function(x) lst()),
  name = c("Model","1/4 mile time","Miles per gallon","Weight","Number of cylinders","Carburetors","Displacement","Horsepower","Engine type","Rear axle ratio","Transmission","Forward gears"),
  palette = c(NA, "perf_palette", rep("overall_palette", 2), rep("engine_palette", 5), rep("transmission_palette", 3)),
  geom = c("text","bar","bar","bar","rect","rect","funkyrect","funkyrect","circle","funkyrect","rect","rect")
)
cinfo <- cinfo %>%
  add_row(id="cyl",  group="Engine",       name="", geom="text", options=lst(lst(overlay=TRUE)), palette="black", .before=6) %>%
  add_row(id="carb", group="Engine",       name="", geom="text", options=lst(lst(overlay=TRUE)), palette="black", .before=8) %>%
  add_row(id="am",   group="Transmission", name="", geom="text", options=lst(lst(overlay=TRUE)), palette="black", .before=14) %>%
  add_row(id="gear", group="Transmission", name="", geom="text", options=lst(lst(overlay=TRUE)), palette="black", .before=17)

palettes <- list(
  perf_palette="Blues", overall_palette="Greens",
  engine_palette="YlOrBr", transmission_palette="Reds",
  black=c("black","black"),
  funky_palette_grey=rev(RColorBrewer::brewer.pal(9,"Greys")[-1])
)
column_groups <- tibble(
  Category=c("Performance","Overall","Engine","Transmission"),
  group=c("Performance","Overall","Engine","Transmission"),
  palette=c("perf_palette","overall_palette","engine_palette","transmission_palette")
)

# image swap
data[data$am==0,"am"]<-"automatic"; data[data$am==1,"am"]<-"manual"
data[data$vs==0,"vs"]<-"vengine";   data[data$vs==1,"vs"]<-"straight"
cinfo$directory<-NA; cinfo$extension<-NA
cinfo <- cinfo[-14, ]
cinfo[cinfo$id %in% c("vs","am"),"directory"]<-"images"
cinfo[cinfo$id %in% c("vs","am"),"extension"]<-"png"
cinfo[c(11,13),"geom"]<-"image"

row_info <- data %>% transmute(id, group=ifelse(grepl("Merc", id),"Mercedes","Other"))
data    <- data[order(row_info$group),]
row_info <- row_info[order(row_info$group),]
row_groups <- tibble(level1=c("Mercedes","Other cars"), group=c("Mercedes","Other"))

# legends
legends <- list(
  list(palette="perf_palette",   geom="bar", title="1/4 mile time",
       labels=c(paste0(min(data$qsec),"s"), rep("",8), paste0(max(data$qsec),"s"))),
  list(palette="overall_palette",geom="bar", title="Miles per gallon",
       labels=c(paste0(min(data$mpg),"mpg"), rep("",8), paste0(max(data$mpg),"mpg"))),
  list(palette="overall_palette",geom="bar", title="Weight",
       labels=c(paste0(min(data$wt),"lbs"), rep("",8), paste0(max(data$wt),"lbs"))),
  list(palette="funky_palette_grey", geom="funkyrect", title="Overall", enabled=TRUE,
       labels=c("0","","0.2","","0.4","","0.6","","0.8","","1")),
  list(palette="engine_palette", enabled=FALSE),
  list(palette="transmission_palette", enabled=FALSE)
)

# width tweaks
cinfo[[1, "options"]] <- list(list(width=6))
cinfo[[2, "options"]] <- list(list(width=6))
cinfo[[3, "options"]] <- list(list(width=3))
cinfo[[4, "options"]] <- list(list(width=3))
cinfo[[12, "options"]] <- list(list(width=1.85))
cinfo[[13, "options"]] <- list(list(width=1.85))

g <- funky_heatmap(data=data, column_info=cinfo, column_groups=column_groups,
                   palettes=palettes, legends=legends, row_info=row_info, row_groups=row_groups)
ggsave(file.path(out_dir,"getting_started_R.png"), g, width=g$width, height=g$height,
       dpi=150, limitsize=FALSE)
cat("wrote getting_started_R.png\n")
