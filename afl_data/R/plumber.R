FIRST_AFL_SEASON = '1897-01-01'

matches = modules::import("matches")
players = modules::import("players")

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
  players$player_results
}
