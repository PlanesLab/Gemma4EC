# rhea500_figure.R — Rhea500 benchmark figures (results/seeds_rhea500/benchmark_*.csv) -> figures/seeds/rhea500/
#   fig_rhea500_benchmark   A  MCC / Precision / Recall   B  MCC per EC class
#   fig_rhea500_main        A metric bars, B per EC class, C EC levels
#
# Usage: Rscript figures/rhea500_figure.R

suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(ggplot2); library(cowplot); library(readr)
})

root    <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))), ".."))
res_dir <- file.path(root, "results", "seeds_rhea500")
out_dir <- file.path(root, "figures", "seeds", "rhea500")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# ---- Methods (as in seed_figures.R) ----
rename_map <- c("Gemma4EC-9B" = "Gemma4EC-9B")   # CSVs already use the figure names
groups <- list(
  "Domain-Specific Models"   = c("Gemma4EC-9B", "Gemma4EC-2B", "BEC-Pred", "Theia", "CLAIRE"),
  "Similarity-Based Methods" = c("SelenzymeRF", "SIMMER"),
  "General-Purpose LLMs"     = c("Gemini", "GPT")
)
pastel_colors <- c(
  "Gemma4EC-9B" = "#685477", "Gemma4EC-2B" = "#B7A5E2", "BEC-Pred" = "#A6DCE0", "Theia" = "#3D6E82",
  "CLAIRE" = "#C8D67E", "SelenzymeRF" = "#C8693F", "SIMMER" = "#EBD95E", "Gemini" = "#D2909F", "GPT" = "#D85A4C"
)
f6_font <- "Liberation Sans"
order_all <- unlist(groups, use.names = FALSE)

drop_methods <- character(0)

ci95 <- function(x) { n <- sum(!is.na(x)); if (n < 2) NA_real_ else qt(0.975, n - 1) * sd(x, na.rm = TRUE) / sqrt(n) }
dpi_max <- function(w_in, h_in, max_px = 39.9e6) min(600, floor(sqrt(max_px / (w_in * h_in))))
save_both <- function(plot, name, width, height) {
  ggsave(file.path(out_dir, paste0(name, ".png")), plot, width = width, height = height,
         dpi = dpi_max(width, height), bg = "white", device = ragg::agg_png)
  message("Saved: ", file.path(out_dir, name), ".png")
}
theme_f6 <- function(base = 24) {
  theme_minimal(base_size = base, base_family = f6_font) +
    theme(text = element_text(color = "grey20"), axis.text = element_text(color = "grey35"),
          axis.title = element_text(color = "grey25"), legend.position = "none",
          panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
          panel.grid.major.y = element_line(color = "grey92", linewidth = 0.35),
          plot.background = element_rect(fill = "white", color = NA),
          plot.margin = margin(8, 10, 8, 10))
}

# ---- Data: only methods with all 10 samples ----
seed_m <- read_csv(file.path(res_dir, "benchmark_seed_metrics.csv"), show_col_types = FALSE) %>%
  filter(!method %in% drop_methods) %>%
  mutate(Model = recode(method, !!!rename_map)) %>%
  group_by(Model) %>% filter(n_distinct(seed) == 10) %>% ungroup() %>%
  filter(Model %in% order_all)
models <- order_all[order_all %in% seed_m$Model]
seed_m <- seed_m %>% mutate(Model = factor(Model, levels = models))

s1 <- seed_m %>% pivot_longer(c(mcc, ppv, recall), names_to = "Metric", values_to = "value") %>%
  mutate(Metric = factor(recode(Metric, mcc = "MCC", ppv = "Precision", recall = "Recall"),
                         levels = c("MCC", "Precision", "Recall"))) %>%
  group_by(Metric, Model) %>% summarise(mean = mean(value), ci = ci95(value), .groups = "drop")

# ---- A: metric bars ----
pA <- ggplot(s1, aes(Metric, mean, fill = Model)) +
  geom_col(position = position_dodge(width = 0.86), width = 0.8) +
  geom_errorbar(aes(ymin = pmax(mean - ci, 0), ymax = pmin(mean + ci, 1)),
                position = position_dodge(width = 0.86), width = 0.42, linewidth = 0.95, color = "grey20") +
  geom_text(aes(y = pmin(mean + ci, 1), label = sub("^0", "", sprintf("%.2f", mean))),
            position = position_dodge(width = 0.86), vjust = -0.4, size = 6.5, fontface = "bold", color = "grey20", family = f6_font) +
  scale_fill_manual(values = pastel_colors) +
  scale_y_continuous(breaks = seq(0, 1, 0.2), expand = c(0, 0)) +
  coord_cartesian(ylim = c(0, 1.06)) +
  labs(x = NULL, y = NULL) +
  theme_f6() + theme(axis.text.x = element_text(size = 38, face = "bold", color = "grey20"), axis.text.y = element_text(size = 30),
                     plot.margin = margin(60, 10, 2, 30))

group_legend <- function(m, title) {
  fake <- data.frame(Model = factor(m, levels = m), y = 1)
  p <- ggplot(fake, aes(Model, y, fill = Model)) + geom_col() +
    scale_fill_manual(values = pastel_colors[m], breaks = m, name = sub(" ", "\n", title)) +
    guides(fill = guide_legend(ncol = 1, title.position = "top")) +
    theme_minimal(base_size = 36, base_family = f6_font) +
    theme(legend.title = element_text(face = "bold", size = 30, lineheight = 0.9, color = "grey20", margin = margin(b = 10)),
          legend.text = element_text(size = 30, color = "grey25", margin = margin(l = 12)),
          legend.key.size = unit(1.35, "cm"), legend.key.spacing.y = unit(0.22, "cm"),
          legend.justification = c(0, 0.5), legend.location = "plot")
  cowplot::ggdraw() + cowplot::draw_grob(cowplot::get_legend(p), x = 0.04, width = 0.96, hjust = 0)
}
n_items <- sapply(groups, function(g) sum(g %in% models)); n_items <- n_items[n_items > 0]
legA <- cowplot::plot_grid(plotlist = c(list(NULL), lapply(names(n_items), function(g) group_legend(groups[[g]][groups[[g]] %in% models], g)), list(NULL)),
                           ncol = 1, rel_heights = c(0.3, n_items + 3.4, 0.3))

# ---- B: MCC per EC class (method colour, EC1 light -> EC7 dark) ----
mix_with_white <- function(color, fraction) {
  v <- grDevices::col2rgb(color)[, 1] * (1 - fraction) + 255 * fraction
  grDevices::rgb(v[1], v[2], v[3], maxColorValue = 255)
}
shades <- lapply(pastel_colors, function(color)
  vapply(seq(0.60, -0.40, length.out = 7), function(f)
    if (f >= 0) mix_with_white(color, f) else {
      v <- grDevices::col2rgb(color)[, 1] * (1 + f); grDevices::rgb(v[1], v[2], v[3], maxColorValue = 255) },
    character(1)))
sB <- read_csv(file.path(res_dir, "benchmark_per_class_metrics.csv"), show_col_types = FALSE, col_types = cols(ec_class = "c")) %>%
  filter(!method %in% drop_methods) %>% mutate(Model = recode(method, !!!rename_map)) %>%
  filter(Model %in% models, metric == "mcc") %>%
  group_by(Model, ec_class) %>% summarise(mean = mean(value), ci = ci95(value), .groups = "drop") %>%
  mutate(Model = factor(Model, levels = models), EC = factor(ec_class, levels = as.character(1:6))) %>% filter(!is.na(EC)) %>%
  rowwise() %>% mutate(fillcol = shades[[as.character(Model)]][as.integer(EC)]) %>% ungroup()
pB <- ggplot(sB, aes(EC, mean, fill = fillcol)) +
  geom_col(width = 0.82) +
  geom_errorbar(aes(ymin = pmax(mean - ci, -1), ymax = pmin(mean + ci, 1)), width = 0.4, linewidth = 0.75, color = "grey35") +
  facet_wrap(~ Model, ncol = 3) +
  scale_fill_identity() +
  scale_x_discrete(labels = function(x) paste0("EC", x)) +
  scale_y_continuous(limits = c(min(0, min(sB$mean - sB$ci, na.rm = TRUE)), 1.02), breaks = seq(0, 1, 0.25)) +
  labs(x = NULL, y = "MCC") +
  theme_f6() +
  theme(strip.text = element_text(size = 26, face = "bold", color = "grey20"), panel.spacing.x = unit(1.2, "lines"),
        panel.spacing.y = unit(1, "lines"), axis.text.x = element_text(size = 21, color = "grey25"),
        axis.text.y = element_text(size = 24), axis.title.y = element_text(size = 30))

top <- cowplot::plot_grid(pA, legA, ncol = 2, rel_widths = c(2.6, 1))
fig <- cowplot::plot_grid(top, pB, ncol = 1, rel_heights = c(1, 1.15), labels = c("A", "B"),
                          label_size = 30, label_fontfamily = f6_font)
save_both(fig, "fig_rhea500_benchmark", 18, 22)

# ---- Main-figure layout (as fig_main_benchmark in figures/seed_figures.R): A metric bars,
#      B MCC per EC class, C MCC across EC levels on a cut y-axis ----

star <- identity

pA_m <- ggplot(s1, aes(Metric, mean, fill = Model)) +
  geom_col(position = position_dodge(width = 0.86), width = 0.8) +
  geom_errorbar(aes(ymin = pmax(mean - ci, 0), ymax = pmin(mean + ci, 1)),
                position = position_dodge(width = 0.86), width = 0.42, linewidth = 0.95, color = "grey20") +
  geom_text(aes(y = pmin(mean + ci, 1), label = sub("^0", "", sprintf("%.2f", mean))),
            position = position_dodge(width = 0.86), vjust = -0.4, size = 11.3, fontface = "bold",
            color = "grey20", family = f6_font) +
  scale_fill_manual(values = pastel_colors, labels = star) +
  scale_y_continuous(breaks = seq(0, 1, 0.2), expand = c(0, 0)) +
  # axis starts at 0.15, or just below the lowest bar if one is lower (bars are cut, not rescaled)
  coord_cartesian(ylim = c(min(0.15, max(0, floor((min(s1$mean, na.rm = TRUE) - 0.04) * 20) / 20)), 1.05)) +
  labs(x = NULL, y = NULL) +
  theme_f6() + theme(axis.text.x = element_text(size = 38, face = "bold", color = "grey20"),
                     axis.text.y = element_text(size = 30), plot.margin = margin(85, 10, 2, 30))

legend_m <- function(m, title) {
  fake <- data.frame(Model = factor(m, levels = m), y = 1)
  p <- ggplot(fake, aes(Model, y, fill = Model)) + geom_col() +
    scale_fill_manual(values = pastel_colors[m], breaks = m, labels = star(m), name = title) +
    guides(fill = guide_legend(ncol = 1, title.position = "top")) +
    theme_minimal(base_size = 42, base_family = f6_font) +
    theme(legend.title = element_text(face = "bold", size = 46, color = "grey20", margin = margin(b = 12)),
          legend.text = element_text(size = 42, color = "grey25", margin = margin(l = 14, r = 14)),
          legend.key.size = unit(2.1, "cm"), legend.key.spacing.y = unit(0.4, "cm"),
          legend.justification = c(0, 0.5), legend.location = "plot")
  cowplot::ggdraw() + cowplot::draw_grob(cowplot::get_legend(p), x = 0.04, width = 0.96, hjust = 0)
}
main_h <- 26; h_A <- 1; h_BC <- 0.95
blk_cm <- n_items * 2.5 + 3.5; row_cm <- main_h * 2.54 * h_A / (h_A + h_BC); pad_A <- max(0, (row_cm - sum(blk_cm)) / 2)
legA_m <- cowplot::plot_grid(plotlist = c(list(NULL), lapply(names(n_items), function(g) legend_m(groups[[g]][groups[[g]] %in% models], g)), list(NULL)),
                             ncol = 1, rel_heights = c(pad_A, blk_cm, pad_A))
rowA <- cowplot::plot_grid(pA_m, legA_m, ncol = 2, rel_widths = c(2.6, 1),
                           labels = c("A", ""), label_size = 80, label_fontfamily = f6_font)

pB_m <- pB + facet_wrap(~ Model, ncol = 3, labeller = as_labeller(star)) +
  theme(plot.margin = margin(85, 10, 8, 10))

# C: one line plot of all methods with a cut y-axis: upper part zoomed on the domain-specific
# models, lower part for the rest; "//" marks the cut.
sC <- read_csv(file.path(res_dir, "benchmark_level_metrics.csv"), show_col_types = FALSE) %>%
  filter(!method %in% drop_methods) %>% mutate(Model = recode(method, !!!rename_map)) %>% filter(Model %in% models) %>%
  group_by(Model, level) %>% summarise(mean = mean(mcc), ci = ci95(mcc), .groups = "drop") %>%
  mutate(Model = factor(Model, levels = models),
         Level = factor(c("Class", "Subclass", "Sub-subclass")[level], levels = c("Class", "Subclass", "Sub-subclass")),
         dom = as.character(Model) %in% c(groups[["Domain-Specific Models"]], "SelenzymeRF"))
top_lo <- floor((min(sC$mean[sC$dom] - sC$ci[sC$dom], na.rm = TRUE) - 0.002) * 100) / 100
top_hi <- ceiling((max(sC$mean[sC$dom] + sC$ci[sC$dom], na.rm = TRUE) + 0.002) * 100) / 100
bot_hi <- ceiling((max(sC$mean[!sC$dom] + sC$ci[!sC$dom], na.rm = TRUE) + 0.01) * 20) / 20
bot_lo <- floor((min(sC$mean[!sC$dom] - sC$ci[!sC$dom], na.rm = TRUE) - 0.01) * 20) / 20
line_part <- function(d, lo, hi, show_x) {
  ggplot(d, aes(Level, mean, color = Model, group = Model)) +
    geom_line(linewidth = 2.4) +
    geom_point(shape = 16, size = 9) +
    scale_color_manual(values = pastel_colors) +
    scale_x_discrete(expand = expansion(add = c(0.4, 0.4))) +
    scale_y_continuous(breaks = scales::breaks_pretty(5), labels = function(x) sprintf("%.2f", x)) +
    coord_cartesian(xlim = c(0.75, 3.25), ylim = c(lo, hi), expand = FALSE, clip = "off") +
    labs(x = NULL, y = NULL) +
    theme_f6() + theme(axis.text = element_text(size = 28),
                       axis.text.x = if (show_x) element_text(size = 32) else element_blank(),
                       plot.margin = margin(if (show_x) 6 else 140, 15, if (show_x) 8 else 6, 10))
}
pC_cut <- cowplot::plot_grid(line_part(sC %>% filter(dom), top_lo, top_hi, FALSE),
                             line_part(sC %>% filter(!dom), bot_lo, bot_hi, TRUE),
                             ncol = 1, align = "v", axis = "lr", rel_heights = c(1.1, 1))
cut_x <- 0.085; cut_y <- 1 / 2.1
pC_cut <- cowplot::ggdraw(pC_cut) +
  cowplot::draw_line(x = cut_x + c(-0.010, 0.010), y = cut_y + 0.006 + c(-0.010, 0.010), size = 1.6, color = "grey30") +
  cowplot::draw_line(x = cut_x + c(-0.010, 0.010), y = cut_y - 0.012 + c(-0.010, 0.010), size = 1.6, color = "grey30")
pC_cut <- cowplot::ggdraw() + cowplot::draw_label("MCC", x = 0.03, angle = 90, size = 32, color = "grey25", fontfamily = f6_font) +
  cowplot::draw_plot(pC_cut, x = 0.05, width = 0.95)

rowBC <- cowplot::plot_grid(pB_m, pC_cut, ncol = 2, rel_widths = c(2.7, 2.1),
                            labels = c("B", "C"), label_size = 80, label_fontfamily = f6_font)
fig_main <- cowplot::plot_grid(rowA, rowBC, ncol = 1, rel_heights = c(h_A, h_BC))
save_both(fig_main, "fig_rhea500_main", 34, main_h)
