match_results <- function(fetch_data, start_date, end_date) {
  data <- if (fetch_data) {
    fitzRoy::get_match_results()
  } else {
    fitzRoy::match_results
  }

  data %>%
    dplyr::filter(., Date >= start_date & Date <= end_date) %>%
    dplyr::rename_all(dplyr::funs(stringr::str_to_lower(.) %>% stringr::str_replace_all(., "\\.", "_")))
}
