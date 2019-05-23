EARLIEST_VALID_SEASON = 2004

#' Fetches fixture data via the fitzRoy package and filters by date range.
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @export
fetch_fixtures <- function(start_date, end_date) {
  first_season = lubridate::year(start_date)
  last_season = lubridate::year(end_date)

  if (first_season < EARLIEST_VALID_SEASON) {
    warning(
      paste0(
        first_season,
        " is earlier than available data. Fetching fixture data between ",
        EARLIEST_VALID_SEASON, " and ", last_season
      )
    )
  }

  max(first_season, EARLIEST_VALID_SEASON):last_season %>%
    purrr::map(fitzRoy::get_fixture) %>%
    dplyr::bind_rows(.) %>%
    dplyr::filter(., Date >= start_date & Date <= end_date) %>%
    dplyr::rename_all(
      ~ stringr::str_to_lower(.) %>% stringr::str_replace_all(., "\\.", "_")
    )
}
