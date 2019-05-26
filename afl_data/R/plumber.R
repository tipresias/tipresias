source(paste0(getwd(), "/R/matches.R"))
source(paste0(getwd(), "/R/players.R"))
source(paste0(getwd(), "/R/betting-odds.R"))
source(paste0(getwd(), "/R/fixtures.R"))
source(paste0(getwd(), "/R/rosters.R"))

FIRST_AFL_SEASON = "1897-01-01"
END_OF_YEAR = past0(lubridate::ymd(Sys.Date() %>% lubridate::year, "12-31"))

#' Return match results data
#' @param fetch_data Whether to fetch fresh data from afltables.com
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /matches
function(
  fetch_data = FALSE, start_date = FIRST_AFL_SEASON, end_date = Sys.Date()
) {
  fetch_match_results(fetch_data, start_date, end_date) %>%
    jsonlite::toJSON(.)
}

#' Return player data
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /players
function(start_date = FIRST_AFL_SEASON, end_date = Sys.Date()) {
  fetch_player_results(start_date, end_date) %>%
    jsonlite::toJSON(.)
}

#' Return betting data along with some basic match data
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /betting_odds
function(start_date = FIRST_AFL_SEASON, end_date = Sys.Date()) {
  fetch_betting_odds(start_date, end_date) %>%
    jsonlite::toJSON(.)
}

#' Return fixture data (match data without results)
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /fixtures
function(start_date = FIRST_AFL_SEASON, end_date = END_OF_YEAR) {
  fetch_fixtures(start_date, end_date) %>%
    jsonlite::toJSON(.)
}

#' Return team rosters for a given round (current season only)
#' @param round_number Fetch the rosters from this round. Note that missing param defaults to current round
#' @get /rosters
function(round_number = NULL) {
  fetch_rosters(round_number) %>%
    jsonlite::toJSON(.)
}
