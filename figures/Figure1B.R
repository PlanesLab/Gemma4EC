library(tidyverse)
library(ggplot2)

df <- read.csv("/Users/josefinaarcagni/Downloads/file1_weighted_metrics.csv")

# ---- Reshape to long format ----
plot_df <- df %>%
  pivot_longer(
    cols = c(Weighted_MCC, Weighted_PPV, Weighted_Recall),
    names_to = "Metric",
    values_to = "Value"
  ) %>%
  mutate(
    Metric = recode(Metric,
                    Weighted_MCC = "MCC",
                    Weighted_PPV = "Precision",
                    Weighted_Recall = "Recall"
    )
  )

# ---- Optional: rename models for nicer labels ----
plot_df$Model <- recode(plot_df$Model,
                        "Gemma4EC-9b" = "Gemma4EC-9B",
                        "Gemma4EC-2b" = "Gemma4EC-2B",
                        "Gemini-2.5-flash" = "Gemini-2.5",
                        "ChatGPT-5.1" = "GPT-5.1",
                        "ChatGPT-5.2" = "GPT-5.2",
                        "ChatGPT-4.1-mini" = "GPT-4.1-mini",
                        "BEC-Pred" = "BEC-Pred",
                        "TxGemma-9b" = "TxGemma-9B"
                        
)

# ---- Ordering ----
plot_df$Model <- factor(plot_df$Model,
                        levels = c("Gemma4EC-9B", "Gemma4EC-2B", "TxGemma-9B","BEC-Pred", "Gemini-2.5", "GPT-5.2",
                                   "GPT-5.1", "GPT-4.1-mini")
)

plot_df$Metric <- factor(plot_df$Metric,
                         levels = c("MCC", "Precision", "Recall")
)

# ---- Hardcode tiny value for TxGemma-9b ----
plot_df <- plot_df %>%
  mutate(
    PlotValue = ifelse(Model == "TxGemma-9B" & Value < 0.01, 0.008, Value),
    LabelValue = ifelse(Model == "TxGemma-9B" & Value < 0.01,
                        "0.00",
                        sprintf("%.2f", Value))
  )

# Without TxGemma
plot_df_no_tx <- plot_df %>%
  filter(Model != "TxGemma-9B")

# Without TxGemma AND BEC-Pred
plot_df_no_tx_bec <- plot_df %>%
  filter(!Model %in% c("TxGemma-9B", "BEC-Pred"))


# ---- Colors ----
pastel_colors <- c(
  "Gemma4EC-9B" = "#C8B8E8",
  "Gemma4EC-2B" = "#D6CFE8",
  "Gemini-2.5"  = "#E8C97A",
  "BEC-Pred"= "#A8DDB5",
  "GPT-5.2" = "#BF7E92",
  "GPT-5.1" = "#D9A3AE",
  "GPT-4.1-mini"= "#E8B7C2",
  "TxGemma-9B"  = "#8FBFE0"
)
make_plot <- function(data) {
  ggplot(data, aes(x = Metric, y = PlotValue, fill = Model)) +
    geom_bar(stat = "identity",
             position = position_dodge(width = 0.90),
             width = 0.75,
             color = "white",
             linewidth = 0.3) +
    geom_text(aes(label = LabelValue),
              position = position_dodge(width = 0.90),
              vjust = -0.3,
              size = 7.2,
              color = "grey30",
              fontface = "bold") +
    scale_fill_manual(values = pastel_colors) +
    scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
    labs(x = NULL, y = NULL, fill = NULL) +
    theme_minimal(base_size = 18) +
    theme(
      axis.text.x = element_text(size = 28, face = "bold", color = "grey30"),
      axis.text.y = element_text(size = 20, color = "grey40"),
      legend.position = "bottom",
      legend.text = element_text(size = 26),
      plot.background = element_rect(fill = "transparent", color = NA)
    )
}

p_no_tx <- make_plot(plot_df_no_tx)

p_no_tx_bec <- make_plot(plot_df_no_tx_bec)


ggsave(
  "/Users/josefinaarcagni/Documents/Gemma4EC/plot_no_txgemma.png",
  plot = p_no_tx,
  width = 20, height = 10, dpi = 600, bg = "transparent"
)

ggsave(
  "/Users/josefinaarcagni/Documents/Gemma4EC/plot_no_txgemma_no_becpred.png",
  plot = p_no_tx_bec,
  width = 20, height = 10, dpi = 600, bg = "transparent"
)