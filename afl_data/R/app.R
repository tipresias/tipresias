library("dplyr")
library("stringr")

pr <- plumber::plumb("R/plumber.R")
pr$run(host = "0.0.0.0", port = 8001)
