# ============================================================
# Libraries
# ============================================================
library(ggplot2)
library(dplyr)
library(tidyr)
library(readr)
library(cowplot)

# ============================================================
# Load data (NEW)
# ============================================================
data <- read_csv("/scratch/jarcagniriv/Gemma4EC/results/summary/splits_weighted_mcc.csv")

# ============================================================
# Reshape data (WIDE → LONG)  🔥 KEY STEP
# ============================================================
data_long <- data %>%
  pivot_longer(
    cols = -Split,
    names_to = c("Method", "Metric"),
    names_sep = "_",
    values_to = "Value"
  )

# ============================================================
# Method order (adjust if needed)
# ============================================================
method_order <- c("Theia", "BEC-Pred", "Gemma4EC-9b")

# ============================================================
# Colors (same as your original)
# ============================================================
split_colors <- c(
  "Stratified" = "#5FC5C1",
  "Time" = "#E5B85F",
  "Scaffold" = "#B88DC9"
)

# ============================================================
# Prepare data
# ============================================================
data_long <- data_long %>%
  mutate(
    Method = factor(Method, levels = method_order),
    Split  = factor(Split, levels = c("Stratified", "Time", "Scaffold")),
    Metric = factor(Metric, levels = c("MCC", "PPV", "Recall"))
  )

# ============================================================
# Theme
# ============================================================
theme_custom <- theme_minimal(base_size = 28) +
  theme(
    axis.title.x = element_blank(),
    axis.title.y = element_blank(),
    plot.margin = margin(t = 30, r = 10, b = 10, l = 10),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    legend.title = element_blank(),
    legend.text = element_text(size = 28),
    plot.title = element_text(hjust = 0.5, size = 28, face = "bold")
  )

# ============================================================
# Create plots (same structure as your original)
# ============================================================

plot_mcc <- ggplot(filter(data_long, Metric == "MCC"),
                   aes(x = Method, y = Value, fill = Split)) +
  geom_bar(stat = "identity", position = "dodge", width = 0.7) +
  scale_fill_manual(values = split_colors) +
  scale_y_continuous(limits = c(0,1), breaks = seq(0.5,1,0.1), expand = c(0,0)) +
  labs(title = "MCC") +
  coord_cartesian(ylim = c(0.5, 1)) +
  theme_custom +
  theme(legend.position = "none")

plot_ppv <- ggplot(filter(data_long, Metric == "PPV"),
                   aes(x = Method, y = Value, fill = Split)) +
  geom_bar(stat = "identity", position = "dodge", width = 0.7) +
  scale_fill_manual(values = split_colors) +
  scale_y_continuous(limits = c(0,1), breaks = seq(0.5,1,0.1), expand = c(0,0)) +
  labs(title = "Precision") +
  theme_custom +
  coord_cartesian(ylim = c(0.5, 1)) +
  theme(legend.position = "none")

plot_recall <- ggplot(filter(data_long, Metric == "Recall"),
                      aes(x = Method, y = Value, fill = Split)) +
  geom_bar(stat = "identity", position = "dodge", width = 0.7) +
  scale_fill_manual(values = split_colors) +
  scale_y_continuous(limits = c(0,1), breaks = seq(0.5,1,0.1), expand = c(0,0)) +
  labs(title = "Recall") +
  theme_custom +
  coord_cartesian(ylim = c(0.5, 1)) +
  theme(legend.position = "none")

# ============================================================
# Legend
# ============================================================
legend_plot <- get_legend(
  ggplot(data_long, aes(x = Method, y = Value, fill = Split)) +
    geom_bar(stat = "identity", position = "dodge") +
    scale_fill_manual(values = split_colors) +
    theme_minimal(base_size = 26) +
    theme(
      legend.title = element_blank(),
      legend.text = element_text(size = 28)
    )
)

# ============================================================
# Combine plots (paper layout)
# ============================================================
final_plot <- plot_grid(
  plot_grid(
    plot_mcc, plot_ppv, plot_recall,
    ncol = 1,
    labels = c("A", "B", "C"),
    label_size = 40,
    label_x = 0.01,
    label_y = 0.99,
    hjust = 0,
    vjust = 1
  ),
  legend_plot,
  ncol = 2,
  rel_widths = c(5, 1)
)
# ============================================================
# Save
# ============================================================
ggsave(
  "/scratch/jarcagniriv/Gemma4EC/figures/splits.png",
  final_plot,
  width = 16,
  height = 18,
  dpi = 600,
  bg = NA
)

print(final_plot)