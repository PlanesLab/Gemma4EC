# seed_figures.R — figures for the ECReact 10-seed benchmark.
#
# Reads results/seeds_<SPLIT_SET>/ (written by results/seeds/compute_seed_metrics.py) and
# data/ECReact_seeds_<SPLIT_SET>/ and writes PNG + PDF to figures/seeds/<SPLIT_SET>/:
#   1  fig1_metrics_bars       MCC / Precision / Recall, mean over seeds + 95% CI whiskers
#   1b fig1b_mcc_boxplot       per-seed MCC distribution per method
#   2  fig2_per_class_mcc      MCC per EC class (1-7), mean + 95% CI
#   3  fig3_levels             MCC / Precision / Recall at class, subclass, sub-subclass level
#   4  fig4_pvalue_triangle    lower triangle of pairwise paired t-test p-values (Holm), B/W
#   5  fig5_dataset_composition  train / val / test EC-class composition of one seed
#
# Usage:
#   R >= 4.3 with ggplot2, cowplot, dplyr, tidyr (see docs/benchmark.md)
#   Rscript figures/seed_figures.R [split_set] [seed_for_fig5]

suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(ggplot2); library(cowplot); library(readr)
})

args      <- commandArgs(trailingOnly = TRUE)
split_set <- if (length(args) >= 1) args[1] else "strat_dedup"
comp_seed <- if (length(args) >= 2) as.integer(args[2]) else 0
root    <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))), ".."))
res_dir <- file.path(root, "results", paste0("seeds_", split_set))
dat_dir <- file.path(root, "data", paste0("ECReact_seeds_", split_set))
out_dir <- file.path(root, "figures", "seeds", split_set)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

read_res <- function(name, ...) read_csv(file.path(res_dir, name), show_col_types = FALSE, ...)

# ---- Methods: display names, groups, colours ----
rename_map <- c(
  "Gemma4EC-9b" = "Gemma4EC-9B", "Gemma4EC-2b" = "Gemma4EC-2B",
  "TxGemma-9b (no FT)" = "TxGemma-9B", "BEC-Pred" = "BEC-Pred", "Theia" = "Theia", "CLAIRE" = "CLAIRE",
  "SelenzymeRF" = "SelenzymeRF", "SIMMER" = "SIMMER",
  "SelenzymeRF (train DB)" = "SelenzymeRF (train DB)", "SIMMER (train DB)" = "SIMMER (train DB)",
  "Gemini-3.1-flash-lite" = "Gemini", "Gemini-2.5-flash" = "Gemini-2.5",
  "ChatGPT-5.2" = "GPT-5.2", "ChatGPT-5.1" = "GPT-5.1", "ChatGPT-4.1-mini" = "GPT"
)
groups <- list(
  "Domain-Specific Models" = c("Gemma4EC-9B", "Gemma4EC-2B", "TxGemma-9B", "BEC-Pred", "Theia", "CLAIRE"),
  "Similarity-Based Methods" = c("SelenzymeRF (train DB)", "SelenzymeRF", "SIMMER (train DB)", "SIMMER"),
  "General-Purpose LLMs" = c("Gemini", "GPT", "Gemini-3.1-flash-lite", "Gemini-2.5", "GPT-5.2", "GPT-5.1", "GPT-4.1-mini")
)
# Method palette (2026-10-19): colours chosen by the user. (Variable name kept for the rest of the script.)
pastel_colors <- c(
  "Gemma4EC-9B" = "#685477", "Gemma4EC-2B" = "#B7A5E2", "TxGemma-9B" = "#8FBFE0",
  "BEC-Pred" = "#A6DCE0", "Theia" = "#3D6E82", "CLAIRE" = "#C8D67E",
  "SelenzymeRF" = "#C8693F", "SelenzymeRF (train DB)" = "#86C5BE",
  "SIMMER" = "#EBD95E", "SIMMER (train DB)" = "#C4B394",
  "Gemini-3.1-flash-lite" = "#D2909F", "Gemini-2.5" = "#E8C97A",
  "GPT-4.1-mini" = "#D85A4C", "Gemini" = "#D2909F", "GPT" = "#D85A4C", "GPT-5.2" = "#BF7E92", "GPT-5.1" = "#D9A3AE"
)
# Line plots: same hues 30% darker, so thin lines and direct labels stay readable on white
line_colors <- setNames(vapply(pastel_colors, function(h) { v <- col2rgb(h) * 0.7; rgb(v[1], v[2], v[3], maxColorValue = 255) }, ""),
                        names(pastel_colors))
ec_names <- c("1" = "Oxidoreductases", "2" = "Transferases", "3" = "Hydrolases", "4" = "Lyases",
              "5" = "Isomerases", "6" = "Ligases", "7" = "Translocases")

# Methods left out of all figures (display names); results stay in the CSVs
drop_models <- c("TxGemma-9B")

# Only methods with complete predictions (compute_seed_metrics.py writes them to seed_summary.csv)
keep_methods <- read_res("seed_summary.csv")$method
# Similarity tools: show the version run with each tool's own published reference database, labelled
# with the plain tool name. Set SIM_DB=train to show the versions whose database was built from each
# seed's training split instead.
# Which run each similarity tool shows (as the plain tool name); any other variants are hidden.
# Override with SIMMER_SRC / SELENZYME_SRC (exact method names from seed_summary.csv).
sim_src <- c(SIMMER      = Sys.getenv("SIMMER_SRC", "SIMMER (train+val DB, per-class null)"),
             SelenzymeRF = Sys.getenv("SELENZYME_SRC", "SelenzymeRF"))                     # published database
for (tool in names(sim_src)) {
  variants <- grep(paste0("^", tool, "( |$)"), keep_methods, value = TRUE)
  src <- if (sim_src[[tool]] %in% keep_methods) sim_src[[tool]] else tool
  keep_methods <- setdiff(keep_methods, setdiff(variants, src))
  rename_map[[src]] <- tool
}
keep_methods <- keep_methods[!recode(keep_methods, !!!rename_map) %in% drop_models]
order_all    <- unlist(groups, use.names = FALSE)
prep <- function(d) {
  d %>% filter(method %in% keep_methods) %>%
    mutate(Model = factor(recode(method, !!!rename_map), levels = order_all)) %>%
    filter(!is.na(Model)) %>% droplevels()
}
ci95 <- function(x) { n <- sum(!is.na(x)); if (n < 2) NA_real_ else qt(0.975, n - 1) * sd(x, na.rm = TRUE) / sqrt(n) }
summ <- function(d, ...) d %>% group_by(...) %>% summarise(mean = mean(value), ci = ci95(value), n = n(), .groups = "drop")

theme_bench <- function(base = 22) {
  theme_minimal(base_size = base) +
    theme(axis.text = element_text(color = "grey35"), axis.title = element_text(color = "grey25"),
          legend.position = "none", panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
          panel.grid.major.y = element_line(color = "grey90", linewidth = 0.4),
          plot.subtitle = element_text(color = "grey40"),
          plot.background = element_rect(fill = "white", color = NA))
}

# Grouped legend: one block per method group
make_group_legend <- function(models, title) {
  models <- models[models %in% names(pastel_colors)]
  if (length(models) == 0) return(NULL)
  fake <- data.frame(Model = factor(models, levels = models), y = seq_along(models))
  p <- ggplot(fake, aes(Model, y, fill = Model)) + geom_col() +
    scale_fill_manual(values = pastel_colors[models], name = title, breaks = models,
                      labels = models) +
    theme_minimal(base_size = 34) +
    theme(legend.title = element_text(size = 38, face = "bold", color = "grey20"),
          legend.text = element_text(size = 34), legend.key.size = unit(1.6, "cm"),
          legend.key.spacing.y = unit(0.25, "cm"))
  cowplot::get_legend(p)
}
grouped_legend <- function(present) {
  legs <- list(); heights <- c()
  for (g in names(groups)) {
    m <- groups[[g]][groups[[g]] %in% present]
    if (length(m)) { legs[[g]] <- make_group_legend(m, g); heights <- c(heights, length(m) + 1.6) }
  }
  pad <- max(0, 12 - sum(heights)) / 2   # keep blocks compact and vertically centred
  cowplot::plot_grid(plotlist = c(list(NULL), legs, list(NULL)), ncol = 1, rel_heights = c(pad, heights, pad))
}
save_fig <- function(plot, present, name, width = 22, height = 10, legend = TRUE) {
  final <- if (legend) cowplot::plot_grid(plot, grouped_legend(present), ncol = 2, rel_widths = c(3.2, 1.5)) else plot
  for (ext in c("png", "pdf")) ggsave(file.path(out_dir, paste0(name, ".", ext)), final,
                                      width = width, height = height, dpi = dpi_max(width, height), bg = "white")
  message("Saved: ", file.path(out_dir, name), ".{png,pdf}")
}

# PNG resolution: the highest dpi that keeps the image under 40 megapixels (journal limit), capped at 600
dpi_max <- function(w_in, h_in, max_px = 39.9e6) min(600, floor(sqrt(max_px / (w_in * h_in))))

# ---- Data ----
seed_m   <- read_res("seed_metrics.csv") %>% prep()
present  <- levels(seed_m$Model)
long_m   <- seed_m %>% pivot_longer(c(mcc, ppv, recall), names_to = "Metric", values_to = "value") %>%
  mutate(Metric = factor(recode(Metric, mcc = "MCC", ppv = "Precision", recall = "Recall"),
                         levels = c("MCC", "Precision", "Recall")))

star <- function(x) x   # kept so callers stay unchanged

# ---- 1: MCC / Precision / Recall bars with 95% CI whiskers ----
s1 <- summ(long_m, Metric, Model)
n_range <- range(s1$n)
n_label <- if (n_range[1] == n_range[2]) sprintf("n = %d seeds", n_range[1]) else sprintf("%d-%d seeds per method", n_range[1], n_range[2])
y_low   <- min(0, floor(min(seed_m$mcc) * 50) / 50)   # room for slightly negative MCC (e.g. TxGemma)
p1 <- ggplot(s1, aes(Metric, mean, fill = Model)) +
  geom_col(position = position_dodge(width = 0.92), width = 0.88, color = "white", linewidth = 0.3) +
  geom_errorbar(aes(ymin = pmax(mean - ci, 0), ymax = pmin(mean + ci, 1)),
                position = position_dodge(width = 0.92), width = 0.3, linewidth = 0.5, color = "grey25") +
  geom_text(aes(y = pmin(mean + ci, 1), label = sprintf("%.2f", mean)), position = position_dodge(width = 0.92),
            vjust = -0.6, size = 4.8, color = "grey35") +
  scale_fill_manual(values = pastel_colors) +
  scale_y_continuous(limits = c(0, 1.05), breaks = seq(0, 1, 0.2), expand = c(0, 0)) +
  labs(x = NULL, y = NULL, subtitle = sprintf("Mean over seeds (%s), whiskers: 95%% CI", n_label)) +
  theme_bench() + theme(axis.text.x = element_text(size = 24, face = "bold"))
save_fig(p1, present, "fig1_metrics_bars")

# ---- 1b: MCC boxplot ----
mcc_order <- s1 %>% filter(Metric == "MCC") %>% arrange(desc(mean)) %>% pull(Model) %>% as.character()
p1b <- ggplot(seed_m %>% mutate(Model = factor(Model, levels = mcc_order)), aes(Model, mcc, fill = Model)) +
  geom_boxplot(width = 0.65, outlier.shape = NA, color = "grey35", linewidth = 0.4) +
  geom_jitter(width = 0.12, height = 0, size = 1.8, alpha = 0.7, color = "grey25") +
  scale_fill_manual(values = pastel_colors) +
  scale_y_continuous(limits = c(y_low, 1), breaks = seq(0, 1, 0.2)) +
  labs(x = NULL, y = "MCC (sub-subclass)", subtitle = sprintf("Per-seed MCC (%s); box = IQR, line = median", n_label)) +
  theme_bench() + theme(axis.text.x = element_text(angle = 35, hjust = 1, size = 15))
save_fig(p1b, present, "fig1b_mcc_boxplot", width = 18, height = 9)

# ---- 2: per EC class MCC ----
pc <- read_res("per_class_metrics.csv", col_types = cols(ec_class = "c")) %>%
  prep() %>% rename(value = mcc)
s2 <- summ(pc, ec_class, Model) %>%
  mutate(Class = factor(paste0("EC ", ec_class, "\n", ec_names[ec_class]), levels = paste0("EC ", 1:7, "\n", ec_names)))
p2 <- ggplot(s2, aes(Class, mean, fill = Model)) +
  geom_col(position = position_dodge(width = 0.92), width = 0.88, color = "white", linewidth = 0.2) +
  geom_errorbar(aes(ymin = pmax(mean - ci, -1), ymax = pmin(mean + ci, 1)),
                position = position_dodge(width = 0.92), width = 0.3, linewidth = 0.4, color = "grey25") +
  scale_fill_manual(values = pastel_colors) +
  scale_y_continuous(limits = c(min(0, min(s2$mean - s2$ci, na.rm = TRUE)), 1.02), breaks = seq(0, 1, 0.2)) +
  labs(x = NULL, y = "MCC (sub-subclass, within EC class)", subtitle = sprintf("Mean over seeds (%s), whiskers: 95%% CI", n_label)) +
  theme_bench() + theme(axis.text.x = element_text(size = 13))
save_fig(p2, present, "fig2_per_class_mcc", width = 24, height = 9)

# ---- 3: EC hierarchy levels ----
lv <- read_res("level_metrics.csv") %>% prep() %>%
  pivot_longer(c(mcc, ppv, recall), names_to = "Metric", values_to = "value") %>%
  mutate(Metric = factor(recode(Metric, mcc = "MCC", ppv = "Precision", recall = "Recall"), levels = c("MCC", "Precision", "Recall")),
         Level = factor(c("Class", "Subclass", "Sub-subclass")[level], levels = c("Class", "Subclass", "Sub-subclass")))
s3 <- summ(lv, Metric, Level, Model)
p3 <- ggplot(s3, aes(Level, mean, color = Model, group = Model)) +
  geom_line(linewidth = 1.1) +
  geom_errorbar(aes(ymin = pmax(mean - ci, 0), ymax = pmin(mean + ci, 1)), width = 0.08, linewidth = 0.5) +
  geom_point(aes(fill = Model), shape = 21, size = 3.4, color = "white", stroke = 0.9) +
  scale_color_manual(values = line_colors) + scale_fill_manual(values = line_colors) +
  scale_y_continuous(limits = c(min(y_low, min(s3$mean - s3$ci, na.rm = TRUE)), 1), breaks = seq(0, 1, 0.2)) +
  facet_wrap(~ Metric, nrow = 1) +
  labs(x = "EC level", y = NULL, subtitle = sprintf("Mean over seeds (%s), whiskers: 95%% CI", n_label)) +
  theme_bench() + theme(strip.text = element_text(size = 20, face = "bold"), axis.text.x = element_text(size = 13))
save_fig(p3, present, "fig3_levels", width = 24, height = 8)

# ---- 3b: zoom on the top methods (they overlap on the full 0-1 scale) ----
top <- s1 %>% filter(Metric == "MCC") %>% arrange(desc(mean)) %>% slice_head(n = 5) %>% pull(Model) %>% as.character()
s3z <- s3 %>% filter(Model %in% top)
p3b <- p3 %+% s3z +
  scale_y_continuous(limits = c(floor(min(s3z$mean - s3z$ci) * 50) / 50, ceiling(max(s3z$mean + s3z$ci) * 50) / 50), breaks = seq(0, 1, 0.02)) +
  labs(subtitle = sprintf("Top %d methods by MCC, zoomed y-axis (%s), whiskers: 95%% CI", length(top), n_label))
save_fig(p3b, top, "fig3b_levels_top_zoom", width = 24, height = 8)

# ---- 4: pairwise significance, as in the review (ECNumberPrediction Case 1 kegg500 bootstrap figure) ----
# Two-sided paired Wilcoxon signed-rank test (exact) on the per-seed MCC of each pair of methods (seeds are paired: every method
# is evaluated on the same 10 splits), Benjamini-Hochberg correction over all pairs; upper-triangle heatmap coloured
# by the BH-adjusted p (peach = 0, blue = 1). Borrowed methods (BORROW, temporary) are marked with "*".
ord <- mcc_order
mcc_seed <- seed_m %>% mutate(Model = as.character(Model)) %>% select(Model, seed, mcc)
# Exact two-sided Wilcoxon signed-rank p by enumerating all 2^n sign assignments, with mid-ranks for
# tied |differences| (wilcox.test drops to the normal approximation when there are ties).
signrank_exact <- function(d) {
  d <- d[d != 0]; n <- length(d); if (n == 0) return(1)
  r <- rank(abs(d)); obs <- sum(r[d > 0]); mu <- sum(r) / 2
  signs <- as.matrix(expand.grid(rep(list(c(0, 1)), n)))
  w <- as.vector(signs %*% r)
  mean(abs(w - mu) >= abs(obs - mu) - 1e-9)
}
paired_p <- function(m1, m2) {
  d <- inner_join(filter(mcc_seed, Model == m1), filter(mcc_seed, Model == m2), by = "seed")
  if (nrow(d) < 3) return(NA_real_)
  signrank_exact(d$mcc.x - d$mcc.y)
}
pairs4 <- t(combn(ord, 2))
pv <- tibble(Method1 = pairs4[, 1], Method2 = pairs4[, 2]) %>%
  rowwise() %>% mutate(pval = paired_p(Method1, Method2)) %>% ungroup() %>%
  mutate(FDR = p.adjust(pval, "BH"),   # Benjamini-Hochberg FDR-adjusted p
         label = ifelse(FDR < 0.001, "<0.001", sprintf("%.3f", FDR)),
         stars = case_when(FDR < 0.001 ~ "***", FDR < 0.01 ~ "**", FDR < 0.05 ~ "*", TRUE ~ "ns"),
         cell_label = paste0(label, "\n", stars),
         Method1 = factor(Method1, levels = ord), Method2 = factor(Method2, levels = ord))
# All significance tests -> results/seeds_<split>/significance_tests.csv
# (per metric; review test = Wilcoxon rank-sum + BH over all pairs; paired signed-rank and paired t given for reference)
sig_all <- bind_rows(lapply(c(MCC = "mcc", Precision = "ppv", Recall = "recall"), function(col) {
  by <- split(seed_m[[col]], as.character(seed_m$Model))
  bys <- split(seed_m, as.character(seed_m$Model))
  tibble(method_1 = pairs4[, 1], method_2 = pairs4[, 2]) %>% rowwise() %>%
    mutate(n_1 = length(by[[method_1]]), n_2 = length(by[[method_2]]),
           mean_1 = mean(by[[method_1]]), mean_2 = mean(by[[method_2]]), diff_mean = mean_1 - mean_2,
           W_ranksum = unname(suppressWarnings(wilcox.test(by[[method_1]], by[[method_2]])$statistic)),
           p_ranksum = suppressWarnings(wilcox.test(by[[method_1]], by[[method_2]])$p.value),
           p_signedrank = { m <- inner_join(bys[[method_1]][, c("seed", col)], bys[[method_2]][, c("seed", col)], by = "seed")
                            suppressWarnings(wilcox.test(m[[2]], m[[3]], paired = TRUE)$p.value) },
           p_ttest_paired = { m <- inner_join(bys[[method_1]][, c("seed", col)], bys[[method_2]][, c("seed", col)], by = "seed")
                              t.test(m[[2]], m[[3]], paired = TRUE)$p.value }) %>%
    ungroup() %>%
    mutate(metric = names(which(c(MCC = "mcc", Precision = "ppv", Recall = "recall") == col)),
           fdr_ranksum_BH = p.adjust(p_ranksum, "BH"),
           stars_ranksum = case_when(fdr_ranksum_BH < 0.001 ~ "***", fdr_ranksum_BH < 0.01 ~ "**", fdr_ranksum_BH < 0.05 ~ "*", TRUE ~ "ns"),
           fdr_signedrank_BH = p.adjust(p_signedrank, "BH"), fdr_ttest_paired_BH = p.adjust(p_ttest_paired, "BH"))
}))
sig_all <- sig_all %>% select(metric, method_1, method_2, n_1, n_2, mean_1, mean_2, diff_mean, W_ranksum, p_ranksum,
                              fdr_ranksum_BH, stars_ranksum, p_signedrank, fdr_signedrank_BH, p_ttest_paired, fdr_ttest_paired_BH)
write_csv(sig_all, file.path(res_dir, "significance_tests.csv"))
message("Saved: ", file.path(res_dir, "significance_tests.csv"))
p4 <- ggplot(pv, aes(x = Method2, y = Method1, fill = FDR)) +
  geom_tile(color = "white", linewidth = 1.2) +
  geom_text(aes(label = cell_label), size = 6, lineheight = 0.9) +
  scale_fill_gradient(low = "#F5E9E2", high = "#8B9AD0", limits = c(0, 1), breaks = seq(0, 1, 0.25), name = NULL) +
  scale_x_discrete(position = "top", limits = ord, labels = star) +
  scale_y_discrete(limits = rev(ord), labels = star) +
  coord_fixed() + labs(caption = NULL) +
  theme_minimal(base_size = 20) +
  theme(axis.title = element_blank(), axis.text.x.top = element_text(angle = 45, hjust = 0, vjust = 0, size = 19),
        axis.text.y = element_text(size = 20), panel.grid = element_blank(),
        plot.caption = element_text(size = 14, color = "grey45", hjust = 0),
        legend.key.height = unit(1.6, "cm"), legend.text = element_text(size = 20), plot.margin = margin(t = 20, r = 120, b = 10, l = 10),
        plot.background = element_rect(fill = "white", color = NA))
save_fig(p4, present, "fig4_pvalue_triangle", width = 15, height = 12, legend = FALSE)

# ---- 5: dataset composition of one seed ----
comp <- bind_rows(lapply(c("train", "val", "test"), function(s)
  read_csv(file.path(dat_dir, paste0("seed", comp_seed), paste0(s, ".csv")), show_col_types = FALSE, col_types = cols(.default = "c")) %>%
    mutate(Split = s))) %>%
  mutate(ec_class = substr(ec, 1, 1), Split = factor(Split, levels = c("train", "val", "test"), labels = c("Train", "Validation", "Test"))) %>%
  count(Split, ec_class) %>% group_by(Split) %>% mutate(pct = 100 * n / sum(n), total = sum(n)) %>% ungroup() %>%
  mutate(Class = factor(paste0("EC ", ec_class, "\n", ec_names[ec_class]), levels = paste0("EC ", 1:7, "\n", ec_names)))
split_cols <- c("Train" = "#C8B8E8", "Validation" = "#AED6F1", "Test" = "#E8C97A")
tot <- comp %>% distinct(Split, total)
p5 <- ggplot(comp, aes(Class, pct, fill = Split)) +
  geom_col(position = position_dodge(width = 0.85), width = 0.8, color = "white", linewidth = 0.3) +
  geom_text(aes(label = format(n, big.mark = ",")), position = position_dodge(width = 0.85), vjust = -0.4, size = 3.3, color = "grey30") +
  scale_fill_manual(values = split_cols, labels = paste0(tot$Split, " (n = ", format(tot$total, big.mark = ",", trim = TRUE), ")")) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.08))) +
  labs(x = NULL, y = "% of split", fill = NULL,
       subtitle = sprintf("Seed %d (%s split); labels: number of reactions", comp_seed, split_set)) +
  theme_minimal(base_size = 16) +
  theme(legend.position = "top", axis.text = element_text(color = "grey30"), panel.grid.minor = element_blank(),
        plot.background = element_rect(fill = "white", color = NA))
save_fig(p5, present, "fig5_dataset_composition", width = 14, height = 7, legend = FALSE)

# Each method's EC-class bars are a light -> dark ramp of the method's own color (EC 1 lightest),
# so panel B matches A and C; the EC class is read from the x-axis and the key in the caption.
mix_col <- function(a, b, w) { ca <- col2rgb(a); cb <- col2rgb(b); rgb(t(ca * (1 - w) + cb * w) / 255) }
shade_ramp <- function(col, n = 7) colorRampPalette(c(mix_col(col, "white", 0.4), col, mix_col(col, "black", 0.2)))(n)
s2m <- s2 %>% mutate(ECn = factor(ec_class, levels = as.character(1:7)), Model = factor(Model, levels = mcc_order)) %>%
  rowwise() %>% mutate(shade = shade_ramp(pastel_colors[[as.character(Model)]])[as.integer(ec_class)]) %>% ungroup()
ec_key <- paste0("EC class:  ", paste0(1:4, " ", ec_names[1:4], collapse = "  \u00b7  "), "\n",
                 paste0(5:7, " ", ec_names[5:7], collapse = "  \u00b7  "))
pB <- ggplot(s2m, aes(ECn, mean, fill = shade)) +
  geom_col(width = 0.78, color = "white", linewidth = 0.3) +
  geom_errorbar(aes(ymin = pmax(mean - ci, -1), ymax = pmin(mean + ci, 1)), width = 0.3, linewidth = 0.45, color = "grey30") +
  facet_wrap(~ Model, ncol = 4) +
  scale_fill_identity() +
  scale_y_continuous(limits = c(min(0, min(s2m$mean - s2m$ci, na.rm = TRUE)), 1.02), breaks = c(0, 0.5, 1)) +
  labs(x = "EC class", y = "MCC (within EC class)", caption = ec_key) +
  theme_bench(22) +
  theme(strip.text = element_text(size = 20, face = "bold", color = "grey20"), panel.spacing = unit(1, "lines"),
        axis.text = element_text(size = 17), plot.caption = element_text(size = 24, color = "grey25", hjust = 0.5, lineheight = 1.2))
save_fig(pB + labs(subtitle = sprintf("Mean over seeds (%s), whiskers: 95%% CI", n_label)), present,
         "fig2b_per_method_ec_classes", width = 18, height = 12, legend = FALSE)

# ---- 6: composite figure ----
#   A (top): MCC / Precision / Recall bars, grouped legend on the right
#   B (bottom): MCC across EC levels; left all methods, right domain-specific models zoomed; legend spans the right side
f6_font <- "Liberation Sans"
theme_f6 <- function(base = 24) {
  theme_minimal(base_size = base, base_family = f6_font) +
    theme(text = element_text(color = "grey20"), axis.text = element_text(color = "grey35"),
          axis.title = element_text(color = "grey25"), legend.position = "none",
          panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
          panel.grid.major.y = element_line(color = "grey92", linewidth = 0.35),
          plot.background = element_rect(fill = "white", color = NA),
          plot.margin = margin(8, 10, 8, 10))
}
f6_models <- intersect(unlist(groups, use.names = FALSE), mcc_order)   # legend order

# A: bars
sA <- s1 %>% mutate(Model = factor(Model, levels = f6_models))
pA6 <- ggplot(sA, aes(Metric, mean, fill = Model)) +
  geom_col(position = position_dodge(width = 0.86), width = 0.8) +
  geom_errorbar(aes(ymin = pmax(mean - ci, 0), ymax = pmin(mean + ci, 1)),
                position = position_dodge(width = 0.86), width = 0.42, linewidth = 0.95, color = "grey20") +
  geom_text(aes(y = pmin(mean + ci, 1), label = sub("^0", "", sprintf("%.2f", mean))),
            position = position_dodge(width = 0.86), vjust = -0.4, size = 11.3, fontface = "bold", color = "grey20", family = f6_font) +
  scale_fill_manual(values = pastel_colors, labels = star) +
  scale_y_continuous(breaks = seq(0, 1, 0.2), expand = c(0, 0)) +
  # axis starts at 0.15, or just below the lowest bar if one is lower (bars are cut, not rescaled)
  coord_cartesian(ylim = c(min(0.15, max(0, floor((min(sA$mean, na.rm = TRUE) - 0.04) * 20) / 20)), 1.05)) +
  labs(x = NULL, y = NULL) +
  theme_f6() + theme(axis.text.x = element_text(size = 38, face = "bold", color = "grey20"), axis.text.y = element_text(size = 30),
                     axis.title.y = element_text(size = 32),
                     plot.caption = element_text(size = 14, color = "grey45", hjust = 0),
                     plot.margin = margin(85, 10, 2, 30))

# Grouped legend: one horizontal block per method group, side by side under panel A
f6_legend <- function(models, title) {
  fake <- data.frame(Model = factor(models, levels = models), y = 1)
  p <- ggplot(fake, aes(Model, y, fill = Model)) + geom_col() +
    scale_fill_manual(values = pastel_colors[models], breaks = models, labels = star(models), name = title) +
    guides(fill = guide_legend(ncol = 1, title.position = "top")) +
    theme_minimal(base_size = 42, base_family = f6_font) +
    theme(legend.title = element_text(face = "bold", size = 46, color = "grey20", margin = margin(b = 12)),
          legend.text = element_text(size = 42, color = "grey25", margin = margin(l = 14, r = 14)),
          legend.key.size = unit(2.1, "cm"), legend.key.spacing.y = unit(0.4, "cm"), legend.key.spacing.x = unit(0.8, "cm"),
          legend.text.position = "right", legend.margin = margin(0, 0, 0, 0),
          legend.justification = c(0, 0.5), legend.location = "plot")   # left-aligned blocks
  leg <- cowplot::get_legend(p)
  cowplot::ggdraw() + cowplot::draw_grob(leg, x = 0.04, width = 0.96, hjust = 0)
}
leg_blocks <- lapply(names(groups), function(g) { m <- groups[[g]][groups[[g]] %in% f6_models]; if (length(m)) f6_legend(m, g) })
leg_blocks <- Filter(Negate(is.null), leg_blocks)
n_items <- sapply(names(groups), function(g) sum(groups[[g]] %in% f6_models)); n_items <- n_items[n_items > 0]
legA <- cowplot::plot_grid(plotlist = c(list(NULL), leg_blocks, list(NULL)), ncol = 1,
                           rel_heights = c(6, n_items + 1.4, 6))

# B: per-method bar plots of MCC per EC class
review_ec_cols <- c("1" = "#f3aa7c", "2" = "#a5dbbc", "3" = "#8adadf", "4" = "#f3e57c",
                    "5" = "#E58A98", "6" = "#a5a9db", "7" = "#bdbdbd")
# Panel B (2026-10-19, user-specified): each method's EC classes in shades of that method's colour,
# light (EC 1) -> close to the full colour (EC 7); classes are named on the x axis instead of a legend.
mix_with_white <- function(color, fraction) {
  rgb <- grDevices::col2rgb(color)[, 1]
  rgb <- rgb * (1 - fraction) + 255 * fraction
  grDevices::rgb(rgb[1], rgb[2], rgb[3], maxColorValue = 255)
}
# ramp: EC1 = 60% white tint ... EC7 = 40% darker than the method colour
panel_b_palettes <- lapply(pastel_colors, function(color)
  vapply(seq(0.60, -0.40, length.out = 7), function(f)
    if (f >= 0) mix_with_white(color, f) else {
      v <- grDevices::col2rgb(color)[, 1] * (1 + f); grDevices::rgb(v[1], v[2], v[3], maxColorValue = 255) },
    character(1)))
sB <- s2 %>% mutate(Model = factor(as.character(Model), levels = f6_models),
                    EC = factor(ec_class, levels = as.character(1:7)))
sB <- sB %>% rowwise() %>% mutate(fillcol = panel_b_palettes[[as.character(Model)]][as.integer(EC)]) %>% ungroup()
pB6 <- ggplot(sB, aes(EC, mean, fill = fillcol)) +
  geom_col(width = 0.82) +
  geom_errorbar(aes(ymin = pmax(mean - ci, -1), ymax = pmin(mean + ci, 1)), width = 0.4, linewidth = 0.75, color = "grey35") +
  facet_wrap(~ Model, ncol = 3, labeller = as_labeller(function(x) sub(" \\(", "\n(", sub("-flash-lite", "\nflash-lite", star(x))))) +
  scale_fill_identity() +
  scale_x_discrete(labels = function(x) paste0("EC", x)) +
  scale_y_continuous(limits = c(min(0, min(sB$mean - sB$ci, na.rm = TRUE)), 1.02), breaks = seq(0, 1, 0.25)) +
  guides(fill = guide_legend(ncol = 1)) +
  labs(x = NULL, y = "MCC") +
  theme_f6() +
  theme(strip.text = element_text(size = 26, face = "bold", color = "grey20", lineheight = 0.9, vjust = 0), panel.spacing.x = unit(1.2, "lines"),
        panel.spacing.y = unit(1, "lines"), axis.text.x = element_text(size = 21, color = "grey25"),
        axis.text.y = element_text(size = 26),
        axis.title.y = element_text(size = 30),
        legend.position = "right", legend.title = element_text(size = 42, face = "bold"),
        legend.text = element_text(size = 38, margin = margin(l = 12)), legend.key.size = unit(1.6, "cm"),
        legend.key.spacing.y = unit(0.2, "cm"))

# C: EC levels; facet 1 = domain-specific models (zoomed), facet 2 = similarity search + LLMs.
# Direct labels at the right end, nudged apart so close lines stay readable.
spread <- function(y, gap) { o <- order(y); v <- y[o]; for (i in seq_along(v)[-1]) v[i] <- max(v[i], v[i - 1] + gap)
  v <- v - (mean(v) - mean(y[o])); out <- y; out[o] <- v; out }
sC_all <- s3 %>% filter(Metric == "MCC") %>% mutate(Model = factor(Model, levels = f6_models))
sC <- bind_rows(sC_all %>% mutate(Panel = "All methods"),
                sC_all %>% filter(Model %in% groups[["Domain-Specific Models"]]) %>% mutate(Panel = "Domain-specific models (zoom)")) %>%
  mutate(Panel = factor(Panel, levels = c("All methods", "Domain-specific models (zoom)")))
labC <- sC %>% filter(Level == "Sub-subclass", !(Panel == "All methods" & Model %in% groups[["Domain-Specific Models"]])) %>% group_by(Panel) %>%
  mutate(rng = diff(range(c(sC$mean[sC$Panel == first(Panel)] - sC$ci[sC$Panel == first(Panel)],
                            sC$mean[sC$Panel == first(Panel)] + sC$ci[sC$Panel == first(Panel)]), na.rm = TRUE)),
         ylab = spread(mean, rng * 0.05)) %>% ungroup()
pC6 <- ggplot(sC, aes(Level, mean, color = Model, group = Model)) +
  geom_line(linewidth = 1.3) +
  geom_errorbar(aes(ymin = mean - ci, ymax = pmin(mean + ci, 1)), width = 0.05, linewidth = 0.55) +
  geom_point(aes(fill = Model), shape = 21, size = 3.8, color = "white", stroke = 0.9) +
  geom_segment(data = labC, aes(x = 3.04, xend = 3.16, y = mean, yend = ylab), linewidth = 0.4) +
  geom_text(data = labC, aes(x = 3.19, y = ylab, label = star(as.character(Model))), hjust = 0, size = 7,
            family = f6_font, show.legend = FALSE) +
  scale_color_manual(values = line_colors) + scale_fill_manual(values = line_colors) +
  scale_x_discrete(expand = expansion(add = c(0.25, 2.1))) +
  scale_y_continuous(breaks = scales::breaks_pretty(5), labels = function(x) sprintf("%.2f", x)) +
  facet_wrap(~ Panel, nrow = 1, scales = "free_y") +
  labs(x = "EC level", y = "MCC") +
  theme_f6() + theme(strip.text = element_text(size = 23, face = "bold", hjust = 0, color = "grey25"),
                     panel.spacing = unit(1.3, "lines"), axis.text = element_text(size = 20))

left6 <- cowplot::plot_grid(pA6, pC6, ncol = 1, rel_heights = c(1, 0.8), labels = c("A", "B"),
                            label_size = 26, label_fontfamily = f6_font)
fig6 <- cowplot::plot_grid(left6, legA, ncol = 2, rel_widths = c(3.4, 1))
for (ext in c("png", "pdf")) ggsave(file.path(out_dir, paste0("fig6_composite_AB.", ext)), fig6,
                                    width = 18, height = 17, dpi = dpi_max(18, 17), bg = "white",
                                    device = if (ext == "pdf") cairo_pdf else ragg::agg_png)
message("Saved: ", file.path(out_dir, "fig6_composite_AB"), ".{png,pdf}")

# Per-EC-class MCC as its own figure (EC classes coloured as in the review)
for (ext in c("png", "pdf")) ggsave(file.path(out_dir, paste0("fig6b_per_class_mcc.", ext)), pB6 + labs(caption = NULL) +
                                      theme(plot.caption = element_text(size = 14, color = "grey45", hjust = 0)),
                                    width = 18, height = 10, dpi = dpi_max(18, 10), bg = "white",
                                    device = if (ext == "pdf") cairo_pdf else ragg::agg_png)
message("Saved: ", file.path(out_dir, "fig6b_per_class_mcc"), ".{png,pdf}")

# ---- Main benchmark figure: A overall metrics, B MCC per EC class, C MCC across EC levels (line plot) ----
lvl_shade <- function(col) c(Class = mix_col(col, "white", 0.45), Subclass = col, `Sub-subclass` = mix_col(col, "black", 0.25))
sL <- s3 %>% filter(Metric == "MCC") %>% mutate(Model = factor(as.character(Model), levels = f6_models)) %>%
  rowwise() %>% mutate(shade = lvl_shade(pastel_colors[[as.character(Model)]])[[as.character(Level)]]) %>% ungroup()
pL6 <- ggplot(sL, aes(Level, mean, fill = shade)) +
  geom_col(width = 0.75) +
  geom_errorbar(aes(ymin = pmax(mean - ci, 0), ymax = pmin(mean + ci, 1)), width = 0.25, linewidth = 0.45, color = "grey35") +
  geom_text(aes(y = pmin(mean + ci, 1), label = sub("^0", "", sprintf("%.2f", mean))), vjust = -0.5, size = 4.2,
            color = "grey30", family = f6_font) +
  facet_wrap(~ Model, ncol = 4, labeller = as_labeller(star)) +
  scale_fill_identity() +
  scale_x_discrete(labels = c(Class = "Class", Subclass = "Subclass", `Sub-subclass` = "Sub-\nsubclass")) +
  scale_y_continuous(limits = c(0, 1.1), breaks = seq(0, 1, 0.25)) +
  labs(x = "EC level", y = "MCC") +
  theme_f6() +
  theme(strip.text = element_text(size = 17, face = "bold", color = "grey20"), panel.spacing.x = unit(1.2, "lines"),
        panel.spacing.y = unit(1, "lines"), axis.text.x = element_text(size = 13, lineheight = 0.9),
        axis.text.y = element_text(size = 13.5))

rowA_m <- cowplot::plot_grid(pA6 + labs(caption = NULL), legA, ncol = 2, rel_widths = c(3.1, 1))
legB   <- cowplot::get_legend(pB6)
pB_m   <- cowplot::plot_grid(pB6 + theme(legend.position = "none", plot.margin = margin(85, 10, 8, 10)), legB, ncol = 2, rel_widths = c(3.1, 0.8))
# C: one line plot of all methods with a cut y-axis: upper part zoomed on the domain-specific models,
# lower part for the rest; "//" marks the cut. Lines are labelled at their right end.
sCb <- sC_all %>% mutate(dom = Model %in% groups[["Domain-Specific Models"]])
top_lo <- floor((min(sCb$mean[sCb$dom] - sCb$ci[sCb$dom], na.rm = TRUE) - 0.002) * 100) / 100
top_hi <- ceiling((max(sCb$mean[sCb$dom] + sCb$ci[sCb$dom], na.rm = TRUE) + 0.002) * 100) / 100
bot_hi <- ceiling((max(sCb$mean[!sCb$dom] + sCb$ci[!sCb$dom], na.rm = TRUE) + 0.01) * 20) / 20
bot_lo <- floor((min(sCb$mean[!sCb$dom] - sCb$ci[!sCb$dom], na.rm = TRUE) - 0.01) * 20) / 20
lab_part <- function(d, lo, hi) d %>% filter(Level == "Sub-subclass") %>% mutate(ylab = spread(mean, (hi - lo) * 0.11))
line_part <- function(lo, hi, labs_d, show_x, d) {
  ggplot(d, aes(Level, mean, color = Model, group = Model)) +   # each part draws only its own methods
    # same pastel colours as panel A; no CI whiskers; method labels at the right end, in the
    # 30%-darker shade of each colour so the text stays legible
    geom_line(linewidth = 2.4) +
    geom_point(aes(color = Model), shape = 16, size = 9) +   # filled points, no border
    # no line labels: the shared method legend names the lines
    scale_color_manual(values = pastel_colors) + scale_fill_manual(values = pastel_colors) +
    scale_x_discrete(expand = expansion(add = c(0.4, 0.4))) +
    scale_y_continuous(breaks = scales::breaks_pretty(5), labels = function(x) sprintf("%.2f", x)) +
    coord_cartesian(xlim = c(0.75, 3.25), ylim = c(lo, hi), expand = FALSE, clip = "off") +  # clip off is safe: each part holds only its own methods
    labs(x = NULL, y = NULL) +
    theme_f6() + theme(axis.text = element_text(size = 28), axis.title.x = element_text(size = 32),
                       axis.text.x = if (show_x) element_text(size = 32) else element_blank(),
                       plot.margin = margin(if (show_x) 6 else 140, 15, if (show_x) 8 else 6, 10))
}
pC_top <- line_part(top_lo, top_hi, lab_part(sCb %>% filter(dom), top_lo, top_hi), FALSE, sCb %>% filter(dom))
pC_bot <- line_part(bot_lo, bot_hi, lab_part(sCb %>% filter(!dom), bot_lo, bot_hi), TRUE, sCb %>% filter(!dom))
pC_cut <- cowplot::plot_grid(pC_top, pC_bot, ncol = 1, align = "v", axis = "lr", rel_heights = c(1.1, 1))
# "//" cut marks on the y-axis between the two parts (x: left edge of the plotting panel)
cut_x <- 0.085; cut_y <- 1 / 2.1   # x: left edge of the plotting panel within the B column
pC_cut <- cowplot::ggdraw(pC_cut) +
  cowplot::draw_line(x = cut_x + c(-0.010, 0.010), y = cut_y + 0.006 + c(-0.010, 0.010), size = 1.6, color = "grey30") +
  cowplot::draw_line(x = cut_x + c(-0.010, 0.010), y = cut_y - 0.012 + c(-0.010, 0.010), size = 1.6, color = "grey30")
pC_cut <- cowplot::ggdraw() + cowplot::draw_label("MCC", x = 0.03, angle = 90, size = 32, color = "grey25", fontfamily = f6_font) +
  cowplot::draw_plot(pC_cut, x = 0.05, width = 0.95)
# Layout: A (metric bars) on top with the method legend on its right; below, B (EC-level lines) and
# C (per-method EC-class bars) side by side, C with its EC-class legend.
main_h <- 26; h_A <- 1; h_BC <- 0.95   # figure height (in); row heights
# Legend blocks sized in cm (1.6 cm keys + title) and centred vertically on row A
blk_cm <- n_items * 2.5 + 3.5; row_cm <- main_h * 2.54 * h_A / (h_A + h_BC); pad_A <- max(0, (row_cm - sum(blk_cm)) / 2)
legA_m <- cowplot::plot_grid(plotlist = c(list(NULL), leg_blocks, list(NULL)), ncol = 1,
                             rel_heights = c(pad_A, blk_cm, pad_A))
rowA   <- cowplot::plot_grid(pA6 + labs(caption = NULL), legA_m, ncol = 2, rel_widths = c(2.6, 1),
                             labels = c("A", ""), label_size = 80, label_fontfamily = f6_font)
pC_only <- pB6 + theme(legend.position = "none", plot.margin = margin(85, 10, 8, 10))
# C's EC-class legend goes underneath it, in rows
legC_bottom <- cowplot::get_legend(pB6 + guides(fill = guide_legend(nrow = 1)) +
                                     theme(legend.position = "bottom", legend.key.spacing.x = unit(0.25, "cm"),
                                           legend.text = element_text(size = 30, margin = margin(l = 5)),
                                           legend.key.size = unit(0.9, "cm")))
colC   <- pC_only   # EC classes are named on B's x axis; no separate legend   # B spans the full row height
rowBC  <- cowplot::plot_grid(colC, pC_cut, ncol = 2, rel_widths = c(2.7, 2.1),   # B: EC-class bars, C: EC levels
                             labels = c("B", "C"), label_size = 80, label_fontfamily = f6_font)
fig_main <- cowplot::plot_grid(rowA, rowBC, ncol = 1, rel_heights = c(h_A, h_BC))
for (ext in c("png", "pdf")) ggsave(file.path(out_dir, paste0("fig_main_benchmark.", ext)), fig_main,
                                    width = 34, height = main_h, dpi = dpi_max(34, main_h), bg = "white",
                                    device = if (ext == "pdf") cairo_pdf else ragg::agg_png)
message("Saved: ", file.path(out_dir, "fig_main_benchmark"), ".{png,pdf}")

# ---- 7: dataset composition pies (one seed): EC class and EC sub-subclass for train / val / test ----
ec_class_cols <- review_ec_cols
norm_ec3 <- function(ec) sapply(strsplit(ec, ".", fixed = TRUE), function(p) paste(as.integer(p[1:3]), collapse = "."))
pie_dat <- bind_rows(lapply(c("train", "val", "test"), function(s)
  read_csv(file.path(dat_dir, paste0("seed", comp_seed), paste0(s, ".csv")), show_col_types = FALSE, col_types = cols(.default = "c")) %>%
    mutate(Split = s))) %>%
  mutate(ec_class = substr(ec, 1, 1), ec3 = norm_ec3(ec),
         Split = factor(Split, levels = c("train", "val", "test"), labels = c("Train", "Validation", "Test")))
split_lab <- pie_dat %>% count(Split) %>% mutate(lab = paste0(Split, "\n(n = ", format(n, big.mark = ",", trim = TRUE), ")"))
pie_dat <- pie_dat %>% left_join(split_lab %>% select(Split, lab), by = "Split") %>%
  mutate(lab = factor(lab, levels = split_lab$lab))

# Nested pie (sunburst): inner ring = EC class, outer ring = EC subclass (all subclasses, each a
# shade of its class color, aligned with its class); subclasses >= 3% of train are labeled.
norm_ec2 <- function(ec) sapply(strsplit(ec, ".", fixed = TRUE), function(p) paste(as.integer(p[1:2]), collapse = "."))
ec2_key  <- function(x) sapply(strsplit(x, ".", fixed = TRUE), function(p) as.integer(p[1]) * 1000 + as.integer(p[2]))
pie_dat  <- pie_dat %>% mutate(ec2 = norm_ec2(ec))
all_ec2  <- sort(unique(pie_dat$ec2)); all_ec2 <- all_ec2[order(ec2_key(all_ec2))]
sub_cols <- c()
for (cl in as.character(1:7)) {
  members <- all_ec2[substr(all_ec2, 1, 1) == cl]
  if (length(members)) {
    ramp <- colorRampPalette(c(mix_col(ec_class_cols[[cl]], "white", 0.6), ec_class_cols[[cl]],
                               mix_col(ec_class_cols[[cl]], "black", 0.35)))(max(2, length(members)))
    sub_cols <- c(sub_cols, setNames(ramp[seq_along(members)], members))
  }
}
ring <- pie_dat %>% count(lab, ec_class, Sub = ec2) %>%
  mutate(key = ec2_key(Sub)) %>%
  group_by(lab) %>% arrange(ec_class, key, .by_group = TRUE) %>%
  mutate(pct = 100 * n / sum(n), ymax = cumsum(pct), ymin = ymax - pct) %>% ungroup()
inner <- ring %>% group_by(lab, ec_class) %>% summarise(ymin = min(ymin), ymax = max(ymax), pct = sum(pct), .groups = "drop") %>%
  mutate(Class = factor(paste0("EC ", ec_class, " ", ec_names[ec_class]), levels = paste0("EC ", 1:7, " ", ec_names)))

# outer labels: subclasses >= 1.5% of train, same subclasses labeled on every pie
# classes too thin to label inside the inner ring (< 8%) get their % in the legend (equal across splits after rounding)
cls_pct  <- inner %>% group_by(Class) %>% summarise(p = mean(pct), .groups = "drop")
cls_lab  <- setNames(as.character(cls_pct$Class), cls_pct$Class)
small    <- cls_pct$p < 8
cls_lab[small] <- paste0(cls_lab[small], " (", ifelse(cls_pct$p[small] < 1, sprintf("%.1f", cls_pct$p[small]), sprintf("%.0f", cls_pct$p[small])), "%)")
lab_subs <- ring %>% filter(grepl("^Train", lab), pct >= 3, pct < 4) %>% pull(Sub)       # mid-size subclasses, outside
# spread label positions at least `gap` apart, then shift the whole set back inside [1, 99] (one turn = 100)
spread_in <- function(y, gap, top = 99.3) {   # labels keep their position unless they collide; pushed apart downward from the end of the turn
  o <- order(y, decreasing = TRUE); v <- y[o]; v[1] <- min(v[1], top)
  for (i in seq_along(v)[-1]) v[i] <- min(v[i], v[i - 1] - gap)
  out <- y; out[o] <- v; out }
out_lab <- bind_rows(
  inner %>% filter(pct < 8) %>% transmute(lab, ymid = (ymin + ymax) / 2, x0 = 1.2, bold = TRUE,
                                          txt = ifelse(pct < 1, sprintf("%.1f%%", pct), sprintf("%.0f%%", pct))),
  NULL) %>%
  group_by(lab) %>% arrange(ymid, .by_group = TRUE) %>% mutate(ylab = spread_in(ymid, 4.2)) %>% ungroup()
lab_in   <- ring %>% filter(grepl("^Train", lab), pct >= 4) %>% pull(Sub)
out_cls <- inner %>% filter(pct < 8) %>% group_by(lab) %>% arrange(ymin, .by_group = TRUE) %>%
  mutate(ymid = (ymin + ymax) / 2, ylab = ymid,   # each label at its own slice angle, at the arrow tip
         txt = ifelse(pct < 1, sprintf("%.1f%%", pct), sprintf("%.0f%%", pct))) %>% ungroup()                 # inside the ring
fig7 <- ggplot() +
  # rings: inner = EC class, outer = EC subclass
  geom_rect(data = inner, aes(xmin = 0.3, xmax = 1.2, ymin = ymin, ymax = ymax, fill = Class), color = "white", linewidth = 0.9) +
  geom_rect(data = ring, aes(xmin = 1.25, xmax = 2.6, ymin = ymin, ymax = ymax), fill = sub_cols[ring$Sub],
            color = "white", linewidth = 0.6) +
  geom_text(data = inner %>% filter(pct >= 8), aes(x = 0.74, y = (ymin + ymax) / 2, label = sprintf("%.0f%%", pct)),
            size = 15, fontface = "bold", color = "black") +
  # subclass numbers inside the outer ring, plain and small, only where the slice is wide enough (>= 3%)
  geom_text(data = ring %>% filter(pct >= 3), aes(x = 1.93, y = (ymin + ymax) / 2, label = Sub),
            size = 8, color = "black") +
  # small EC classes (< 8%, lyases and smaller): bold % just outside the pie, no leader lines;
  # neighbours are nudged apart in angle only
  # straight radial arrow from just outside the pie to the slice; each label sits at its slice's angle,
  # alternating between two distances so neighbouring labels do not collide
  geom_segment(data = out_cls, aes(x = 2.86, xend = 1.25, y = ymid, yend = ymid), color = "black",
               linewidth = 0.5, arrow = arrow(length = unit(0.25, "cm"), type = "closed")) +
  geom_text(data = out_cls, aes(x = 2.9, y = ylab, label = txt), size = 9.5, fontface = "bold", color = "black", hjust = 0) +
  scale_fill_manual(values = setNames(ec_class_cols, paste0("EC ", 1:7, " ", ec_names)), labels = unname(ec_names), name = NULL, drop = FALSE) +
  coord_polar(theta = "y", direction = -1, start = -pi / 2, clip = "off") +   # small classes sit at 3 o'clock
  scale_y_continuous(limits = c(0, 100), expand = c(0, 0)) +   # one full turn = 100%
  scale_x_continuous(limits = c(0, 2.75), expand = c(0, 0), oob = scales::oob_keep) +   # labels draw beyond the rim (clip off)
  facet_wrap(~ lab, nrow = 1, labeller = as_labeller(function(x) gsub("\n", " ", x))) +   # "Train (n = ...)", in split order
  guides(fill = guide_legend(nrow = 1)) +
  theme_void(base_size = 26) +
  theme(strip.text = element_text(size = 56, face = "bold", color = "black", margin = margin(b = 0)),
        legend.position = "bottom",
        legend.text = element_text(size = 40, color = "black", margin = margin(l = 10, r = 34)), legend.key.size = unit(1.7, "cm"),
        panel.spacing = unit(6, "lines"), legend.margin = margin(t = 40),
        plot.background = element_rect(fill = "white", color = NA), plot.margin = margin(10, 110, 10, 110))
for (ext in c("png", "pdf")) ggsave(file.path(out_dir, paste0("fig7_dataset_pies.", ext)), fig7,
                                    width = 34, height = 14, dpi = dpi_max(34, 14), bg = "white")
message("Saved: ", file.path(out_dir, "fig7_dataset_pies"), ".{png,pdf}")
