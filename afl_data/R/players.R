player_results <- function(start_date, end_date) {
  this_year <- Sys.Date() %>% substring(0, 4) %>% as.integer()

  data <- tryCatch({
      fitzRoy::get_afltables_stats(start_date = start_date, end_date = end_date)
    },
    error = handle_players_route_error(start_date, end_date)
  )

  data %>%
    dplyr::filter(., Date >= start_date & Date <= end_date) %>%
    dplyr::rename_all(dplyr::funs(stringr::str_to_lower(.) %>% stringr::str_replace_all(., "\\.", "_"))) %>%
    jsonlite::toJSON()
}

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
