# ============================================================
# Load data
# ============================================================
data_classes <- read.csv(
  "/scratch/jarcagniriv/Gemma4EC/results/summary/per_class_mcc.csv",
  stringsAsFactors = FALSE
)

# ============================================================
# EC class names
# ============================================================
ec_class_names <- c(
  "1" = "Oxidoreductases",
  "2" = "Transferases",
  "3" = "Hydrolases",
  "4" = "Lyases",
  "5" = "Isomerases",
  "6" = "Ligases",
  "7" = "Translocases"
)

class_colors <- c(
  "Oxidoreductases" = "#f3aa7c",
  "Transferases"    = "#a5dbbc",
  "Hydrolases"      = "#8adadf",
  "Lyases"          = "#f3e57c",
  "Isomerases"      = "#E58A98",
  "Ligases"         = "#a5a9db",
  "Translocases"    = "#bdbdbd"
)

class_order <- c(
  "Oxidoreductases", "Transferases", "Hydrolases",
  "Lyases", "Isomerases", "Ligases", "Translocases"
)

# ============================================================
# METHODS
# ============================================================
selected_methods <- c(
  "Gemma4EC.9b",
  "Gemma4EC.2b",
  "BEC.Pred",
  "Theia",
  "Gemini.2.5.flash",
  "ChatGPT.5.2",
  "ChatGPT.5.1",
  "ChatGPT.4.1.mini"
)

# ============================================================
# METHOD LABELS
# ============================================================
method_labels <- c(
  "Gemma4EC.9b"      = "Gemma4EC-9B",
  "Gemma4EC.2b"      = "Gemma4EC-2B",
  "BEC.Pred"         = "BEC-Pred",
  "Theia"            = "Theia",
  "Gemini.2.5.flash" = "Gemini-2.5",
  "ChatGPT.5.2"      = "GPT-5.2",
  "ChatGPT.5.1"      = "GPT-5.1",
  "ChatGPT.4.1.mini" = "GPT-4.1-mini"
)

# ============================================================
# Libraries
# ============================================================
library(dplyr)
library(tidyr)
library(ggplot2)
library(cowplot)

# ============================================================
# Prepare data (wide → long)
# ============================================================
data_classes <- data_classes %>%
  filter(EC_class != "Weighted_avg") %>%
  mutate(
    ec_class_name = ec_class_names[as.character(EC_class)],
    ec_class_name = factor(ec_class_name, levels = class_order)
  ) %>%
  pivot_longer(
    cols      = all_of(selected_methods),
    names_to  = "method",
    values_to = "class_mcc"
  ) %>%
  mutate(
    method = recode(method, !!!method_labels),
    method = factor(method, levels = method_labels[selected_methods])
  )

# ============================================================
# Create plots per method
# ============================================================
class_mcc_plots <- lapply(levels(data_classes$method), function(m) {

  ggplot(
    filter(data_classes, method == m),
    aes(x = ec_class_name, y = class_mcc, fill = ec_class_name)
  ) +
    geom_bar(stat = "identity") +
    scale_fill_manual(values = class_colors) +
    scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
    labs(title = m) +
    theme_minimal(base_size = 20) +
    theme(
      axis.title       = element_blank(),
      axis.text.x      = element_blank(),
      axis.text.y      = element_text(color = "grey40"),
      panel.grid.major.x = element_blank(),
      panel.grid.minor   = element_blank(),
      legend.position  = "none",
      plot.title       = element_text(hjust = 0.5, face = "bold"),
      plot.margin      = margin(t = 20, r = 10, b = 20, l = 10)
    )
})

# ============================================================
# Shared legend
# ============================================================
legend_b <- cowplot::get_legend(
  ggplot(data_classes, aes(x = ec_class_name, y = class_mcc, fill = ec_class_name)) +
    geom_bar(stat = "identity") +
    scale_fill_manual(values = class_colors, name = NULL) +
    theme_minimal(base_size = 20) +
    theme(legend.text = element_text(size = 22))
)

# ============================================================
# Combine panels
# ============================================================
panel_b_new <- cowplot::plot_grid(
  cowplot::plot_grid(plotlist = class_mcc_plots, ncol = 2),
  legend_b,
  ncol       = 2,
  rel_widths = c(4, 1)
)

# ============================================================
# Save figure
# ============================================================
ggsave(
  "/scratch/jarcagniriv/Gemma4EC/figures/panelB_classes_selected.png",
  panel_b_new,
  width  = 14,
  height = 16,
  dpi    = 600
)
