library(tidyverse)
library(ggplot2)
library(cowplot)

df <- read.csv("/scratch/jarcagniriv/Gemma4EC/results/summary/weighted_metrics.csv")

# ---- Reshape to long format ----
plot_df <- df %>%
  pivot_longer(
    cols = c(Weighted_MCC, Weighted_PPV, Weighted_Recall),
    names_to  = "Metric",
    values_to = "Value"
  ) %>%
  mutate(
    Metric = recode(Metric,
                    Weighted_MCC    = "MCC",
                    Weighted_PPV    = "Precision",
                    Weighted_Recall = "Recall"
    )
  )

# ---- Rename models ----
plot_df$Model <- recode(plot_df$Model,
                        "Gemma4EC-9b"      = "Gemma4EC-9B",
                        "Gemma4EC-2b"      = "Gemma4EC-2B",
                        "Gemini-2.5-flash" = "Gemini-2.5",
                        "ChatGPT-5.1"      = "GPT-5.1",
                        "ChatGPT-5.2"      = "GPT-5.2",
                        "ChatGPT-4.1-mini" = "GPT-4.1-mini",
                        "BEC-Pred"         = "BEC-Pred",
                        "TxGemma-9b"       = "TxGemma-9B",
                        "Theia"            = "Theia"
)

# ---- Group definitions ----
domain_models <- c("Gemma4EC-9B", "Gemma4EC-2B", "TxGemma-9B", "BEC-Pred", "Theia")
llm_models    <- c("Gemini-2.5", "GPT-5.2", "GPT-5.1", "GPT-4.1-mini")

# ---- Ordering ----
plot_df$Model  <- factor(plot_df$Model,  levels = c(domain_models, llm_models))
plot_df$Metric <- factor(plot_df$Metric, levels = c("MCC", "Precision", "Recall"))

# ---- Colors ----
pastel_colors <- c(
  "Gemma4EC-9B"  = "#C8B8E8",
  "Gemma4EC-2B"  = "#D6CFE8",
  "TxGemma-9B"   = "#8FBFE0",
  "BEC-Pred"     = "#A8DDB5",
  "Theia"        = "#AED6F1",
  "Gemini-2.5"   = "#E8C97A",
  "GPT-5.2"      = "#BF7E92",
  "GPT-5.1"      = "#D9A3AE",
  "GPT-4.1-mini" = "#E8B7C2"
)

# ---- Hardcode tiny value for TxGemma-9B ----
plot_df <- plot_df %>%
  mutate(
    PlotValue  = ifelse(Model == "TxGemma-9B" & Value < 0.01, 0.008, Value),
    LabelValue = ifelse(Model == "TxGemma-9B" & Value < 0.01,
                        "0.00", sprintf("%.2f", Value))
  )

# ---- Subsets ----
plot_df_no_tx     <- plot_df %>% filter(Model != "TxGemma-9B")
plot_df_no_tx_bec <- plot_df %>% filter(!Model %in% c("TxGemma-9B", "BEC-Pred"))

# ---- Bar plot (no embedded legend) ----
make_plot <- function(data) {
  ggplot(data, aes(x = Metric, y = PlotValue, fill = Model)) +
    geom_bar(stat = "identity",
             position = position_dodge(width = 0.95),
             width = 0.90,
             color = "white",
             linewidth = 0.3) +
    geom_text(aes(label = LabelValue),
              position = position_dodge(width = 0.95),
              vjust = -0.3,
              size = 7.2,
              color = "grey30",
              fontface = "bold") +
    scale_fill_manual(values = pastel_colors) +
    scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
    labs(x = NULL, y = NULL) +
    theme_minimal(base_size = 18) +
    theme(
      axis.text.x  = element_text(size = 32, face = "bold", color = "grey30"),
      axis.text.y  = element_text(size = 24, color = "grey40"),
      legend.position = "none",
      plot.background = element_rect(fill = "transparent", color = NA)
    )
}

# ---- Grouped legend builder ----
# Extracts a cowplot legend for one group of models with a bold group title.
make_group_legend <- function(models, group_title, colors) {
  models <- models[models %in% names(colors)]
  if (length(models) == 0) return(NULL)

  fake <- data.frame(
    Model = factor(models, levels = models),
    y     = seq_along(models)
  )
  p <- ggplot(fake, aes(x = Model, y = y, fill = Model)) +
    geom_bar(stat = "identity") +
    scale_fill_manual(values = colors[models], name = group_title, breaks = models) +
    theme_minimal(base_size = 22) +
    theme(
      legend.title    = element_text(size = 26, face = "bold", color = "grey20"),
      legend.text     = element_text(size = 26),
      legend.key.size = unit(0.9, "cm")
    )
  cowplot::get_legend(p)
}

# ---- Combine plot + grouped legend and save ----
save_figure <- function(plot_data, out_path, width = 22) {
  present <- as.character(unique(plot_data$Model))
  present <- present[!is.na(present)]

  domain_present <- domain_models[domain_models %in% present]
  llm_present    <- llm_models[llm_models %in% present]

  leg_domain <- make_group_legend(domain_present, "Domain-Specific Models",  pastel_colors)
  leg_llm    <- make_group_legend(llm_present,    "General-Purpose LLMs",   pastel_colors)

  legend_col <- cowplot::plot_grid(
    leg_domain, leg_llm,
    ncol        = 1,
    align       = "v",
    rel_heights = c(length(domain_present), length(llm_present))
  )

  final <- cowplot::plot_grid(
    make_plot(plot_data),
    legend_col,
    ncol       = 2,
    rel_widths = c(4, 1)
  )

  ggsave(out_path, plot = final, width = width, height = 10, dpi = 600, bg = "transparent")
  message("Saved: ", out_path)
}

save_figure(
  plot_df_no_tx,
  "/scratch/jarcagniriv/Gemma4EC/figures/plot_no_txgemma.png"
)

save_figure(
  plot_df_no_tx_bec,
  "/scratch/jarcagniriv/Gemma4EC/figures/plot_no_txgemma_no_becpred.png"
)
