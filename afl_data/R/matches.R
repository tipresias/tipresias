#' Fetches match data via the fitzRoy package and filters by date range.
#' @param fetch_data Whether to fetch fresh data from afltables
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @export
fetch_match_results <- function(fetch_data, start_date, end_date) {
  data <- if (fetch_data) {
    fitzRoy::get_match_results()
  } else {
    fitzRoy::match_results
  }

  data %>%
    dplyr::filter(., Date >= start_date & Date <= end_date) %>%
    dplyr::rename_all(~ stringr::str_to_lower(.) %>% stringr::str_replace_all(., "\\.", "_"))
}
