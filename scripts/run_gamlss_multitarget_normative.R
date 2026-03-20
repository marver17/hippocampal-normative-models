#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(gamlss)
  library(gamlss.dist)
})

args <- commandArgs(trailingOnly = TRUE)
input_file <- if (length(args) >= 1) args[[1]] else "../data/combined/normative_modeling_dataset.csv"
out_dir <- if (length(args) >= 2) args[[2]] else "../models/normative_multitarget"

set.seed(42)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cat("=== GAMLSS MULTI-TARGET NORMATIVE TRAINING ===\n")
cat("Input:", input_file, "\n")
cat("Output dir:", out_dir, "\n\n")

df <- read.csv(input_file)

if (!("source_method" %in% colnames(df))) {
  stop("Colonna source_method non trovata nel dataset.")
}

configs <- list(
  list(target = "hippocampus_etiv_ratio", method = "all"),
  list(target = "hippocampus_etiv_ratio", method = "synthseg"),
  list(target = "hippocampus_etiv_ratio", method = "fastsurfer"),
  list(target = "ilv_to_hippocampal_ratio", method = "fastsurfer")
)

safe_slug <- function(x) {
  gsub("[^A-Za-z0-9_]+", "_", x)
}

fit_one_config <- function(data, target_var, model_method) {
  if (!(target_var %in% colnames(data))) {
    stop(paste("Target non trovato:", target_var))
  }

  keep_cols <- c("age", "sex", "dataset", "source_method", target_var)
  d <- data[, keep_cols, drop = FALSE]
  names(d)[ncol(d)] <- "target"

  if (model_method != "all") {
    d <- d[d$source_method == model_method, , drop = FALSE]
  }

  d <- d[complete.cases(d), , drop = FALSE]
  d <- d[is.finite(d$target) & d$target > 0, , drop = FALSE]

  d$sex <- as.factor(d$sex)
  d$dataset <- as.factor(d$dataset)
  d$source_method <- as.factor(d$source_method)

  # Drop unused levels after filtering to avoid singular design matrices.
  d <- droplevels(d)

  if (nrow(d) < 80) {
    stop(paste("Campione insufficiente dopo filtri:", nrow(d)))
  }

  ctrl <- gamlss.control(n.cyc = 50, trace = FALSE)

  mu_terms <- c("pb(age)")
  if (nlevels(d$sex) > 1) {
    mu_terms <- c(mu_terms, "sex")
  }
  if (nlevels(d$dataset) > 1) {
    mu_terms <- c(mu_terms, "dataset")
  }
  mu_formula <- as.formula(paste("target ~", paste(mu_terms, collapse = " + ")))

  model <- gamlss(
    formula = mu_formula,
    sigma.formula = ~ pb(age),
    nu.formula = ~ 1,
    tau.formula = ~ 1,
    family = BCT(),
    data = d,
    control = ctrl
  )

  # Use fitted() on training data to avoid predict() scope issues with Call$data.
  mu_pred <- fitted(model, what = "mu")
  sigma_pred <- fitted(model, what = "sigma")
  nu_pred <- fitted(model, what = "nu")
  tau_pred <- fitted(model, what = "tau")

  pvals <- pBCT(d$target, mu = mu_pred, sigma = sigma_pred, nu = nu_pred, tau = tau_pred)
  pvals <- pmin(pmax(pvals, 1e-12), 1 - 1e-12)
  z_scores <- qnorm(pvals)

  d_out <- d
  d_out$target_var <- target_var
  d_out$model_method <- model_method
  d_out$mu <- mu_pred
  d_out$sigma <- sigma_pred
  d_out$nu <- nu_pred
  d_out$tau <- tau_pred
  d_out$z_score <- z_scores
  d_out$percentile <- pvals * 100

  list(model = model, data = d_out)
}

summary_rows <- list()

for (cfg in configs) {
  target_var <- cfg$target
  model_method <- cfg$method
  run_name <- paste0(safe_slug(target_var), "__", safe_slug(model_method))

  cat("--- Run:", run_name, "---\n")

  result <- tryCatch(
    fit_one_config(df, target_var, model_method),
    error = function(e) {
      cat("SKIP (errore):", conditionMessage(e), "\n")
      if (!is.null(conditionCall(e))) {
        cat("Call:", deparse(conditionCall(e)), "\n")
      }
      cat("\n")
      NULL
    }
  )

  if (is.null(result)) {
    next
  }

  model_path <- file.path(out_dir, paste0("gamlss_bct_model_", run_name, ".rds"))
  data_path <- file.path(out_dir, paste0("normative_with_zscores_", run_name, ".csv"))

  saveRDS(result$model, model_path)
  write.csv(result$data, data_path, row.names = FALSE)

  s <- data.frame(
    run_name = run_name,
    target_var = target_var,
    model_method = model_method,
    n = nrow(result$data),
    mean_z = mean(result$data$z_score, na.rm = TRUE),
    sd_z = sd(result$data$z_score, na.rm = TRUE),
    min_z = min(result$data$z_score, na.rm = TRUE),
    max_z = max(result$data$z_score, na.rm = TRUE),
    AIC = AIC(result$model),
    SBC = BIC(result$model)
  )
  summary_rows[[length(summary_rows) + 1]] <- s

  cat("OK ->", model_path, "\n")
  cat("OK ->", data_path, "\n\n")
}

if (length(summary_rows) == 0) {
  stop("Nessun modello completato con successo.")
}

summary_df <- do.call(rbind, summary_rows)
summary_path <- file.path(out_dir, "normative_multitarget_summary.csv")
write.csv(summary_df, summary_path, row.names = FALSE)

cat("=== COMPLETATO ===\n")
cat("Summary:", summary_path, "\n")
print(summary_df)
