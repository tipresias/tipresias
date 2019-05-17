FIRST_AFL_SEASON = '1897-01-01'

matches = modules::import("matches")

#' Return match results data
#' @param fetch_data Whether to fetch fresh data from afltables.com
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /matches
function(fetch_data = FALSE, start_date = FIRST_AFL_SEASON, end_date = Sys.Date()) {
  matches$match_results(fetch_data, start_date, end_date)
}

#' Return player data
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /players
function(start_date = FIRST_AFL_SEASON, end_date = Sys.Date()) {
  this_year <- Sys.Date() %>% substring(0, 4) %>% as.integer()

  handle_players_route_error <- function(start_date, end_date) {
    end_date_year <- end_date %>% substring(0, 4) %>% as.integer()

    function(err) {
      if (end_date_year > this_year) {
        retry_with_last_year_end_date(start_date, end_date)
      } else {
        stop(err)
      }
    }
  }

  retry_with_last_year_end_date <- function(start_date, end_date) {
      end_date_last_year <- paste0(this_year - 1, "-12-31")

      warning(
        paste0(
          "end_date of ", end_date, " is in a year for which AFLTables has no ",
          "data. Retrying with an end_date of the end of last year: ",
          end_date_last_year
        )
      )

      fitzRoy::get_afltables_stats(
        start_date = start_date,
        end_date = end_date_last_year
      )
  }

  data <- tryCatch({
      fitzRoy::get_afltables_stats(start_date = start_date, end_date = end_date)
    },
    error = handle_players_route_error(start_date, end_date)
  )

  data %>%
    filter(., Date >= start_date & Date <= end_date) %>%
    dplyr::rename_all(dplyr::funs(stringr::str_to_lower(.) %>% stringr::str_replace_all(., "\\.", "_"))) %>%
    jsonlite::toJSON()
}
