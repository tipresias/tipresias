FIRST_AFL_SEASON = "1897-01-01"

matches = modules::use("R/matches.R")
players = modules::use("R/players.R")
bettingodds = modules::use("R/betting-odds.R")

#' Return match results data
#' @param fetch_data Whether to fetch fresh data from afltables.com
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /matches
function(fetch_data = FALSE, start_date = FIRST_AFL_SEASON, end_date = Sys.Date()) {
  matches$fetch_match_results(fetch_data, start_date, end_date) %>%
    jsonlite::toJSON(.)
}

#' Return player data
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /players
function(start_date = FIRST_AFL_SEASON, end_date = Sys.Date()) {
  players$fetch_player_results(start_date, end_date) %>%
    jsonlite::toJSON(.)
}

#' Return betting data along with some basic match data
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @get /betting_odds
function(start_date = FIRST_AFL_SEASON, end_date = Sys.Date()) {
  bettingodds$fetch_betting_odds(start_date, end_date) %>%
    jsonlite::toJSON(.)
}
