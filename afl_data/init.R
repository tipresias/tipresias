install.packages("devtools")

install.packages("BH")
install.packages("dplyr")
install.packages("plogr")
install.packages("plumber")
install.packages("progress")
install.packages("purrr")
install.packages("rvest")
install.packages("stringr")

# Installing via git rather than github to avoid unauthenticated API
# rate limits in CI
devtools::install_git("git://github.com/jimmyday12/fitzRoy.git")
# Only using master-branch install to get new pivot_wider function.
# Can switch back to CRAN once that gets released
devtools::install_git("git://github.com/tidyverse/tidyr.git")

install.packages("roxygen2")
install.packages("testthat")