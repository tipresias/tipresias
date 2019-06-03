library("magrittr")

port <- as.numeric(Sys.getenv("PORT", unset = "8080"))
pr <- plumber::plumb("R/plumber.R")
pr$run(host = "0.0.0.0", port = port)
