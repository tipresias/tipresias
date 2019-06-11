AFL_DOMAIN = "https://www.afl.com.au"
TEAMS_PATH = "/news/teams"
PLAYER_COL_NAMES = c(
  "player_name",
  "playing_for",
  "home_team",
  "away_team",
  "date",
  "match_id"
)
# As of 30-05-2019 afl.com.au has seen fit to change the structure of the HTML
# on the /news/teams page, adding promotional links to the last 3 positions,
# shifting the match datetime to 4th from last. This only applies to matches
# that haven't been played yet.
PREMATCH_LINKS_COUNT = 3


#' Scrapes team roster data (i.e. which players are playing for each team) for
#' a given round from afl.com.au, cleans it, and returns it as a dataframe.
#' @param round_number Which round to get rosters for
#' @export
fetch_rosters <- function(round_number) {
  parse_date_time <- function(date_time_string) {
    lubridate::parse_date_time(
      date_time_string, "%I:%M%p, %B %d, %Y",
      tz = "Australia/Melbourne",
      quiet = TRUE
    )
  }


  clean_data_frame <- function(roster_df) {
    roster_df %>%
      dplyr::mutate_all(., as.character) %>%
      dplyr::mutate(
        .,
        date = parse_date_time(.$date)
      ) %>%
      dplyr::mutate(., season = lubridate::year(.$date))
  }


  convert_to_data_frame <- function(matches) {
    row_lengths_sum <- matches %>%
      purrr::map(., length) %>%
      purrr::reduce(., sum, .init = 0)

    if (row_lengths_sum == 0) {
      return(
        matrix(ncol = length(PLAYER_COL_NAMES), nrow = 0) %>%
          as.data.frame(.) %>%
          setNames(PLAYER_COL_NAMES)
      )
    }

    matches %>%
      unlist(.) %>%
      matrix(
        .,
        ncol = length(PLAYER_COL_NAMES),
        byrow = TRUE,
        dimnames = list(NULL, PLAYER_COL_NAMES)
      ) %>%
      as.data.frame(.)
  }


  assign_home_away_teams <- function(home_team_player, away_team_player) {
    home_team <- home_team_player["playing_for"] %>% as.character(.)
    away_team <- away_team_player["playing_for"] %>% as.character(.)

    list(
      c(home_team_player, home_team = home_team, away_team = away_team),
      c(away_team_player, home_team = home_team, away_team = away_team)
    )
  }


  collect_players <- function(team_data) {
    team_name = team_data[[1]]

    team_data[2:length(team_data)] %>%
      purrr::map(., ~ c(player_name = ., playing_for = team_name))
  }


  parse_team_data <- function(team_element) {
    team_element %>%
      rvest::html_nodes('li') %>%
      purrr::map(., ~ rvest::html_text(.)) %>%
      purrr::map(., ~ stringr::str_trim(.) %>% stringr::str_split(., "\\s*\\n\\s*")) %>%
      unlist(.) %>%
      purrr::discard(., grepl("\\d", .))
  }


  get_datetime_string <- function(strings) {
    last_index <- length(strings)
    last_string <- strings[[last_index]]
    maybe_date_time <- parse_date_time(last_string)

    if (is.na(maybe_date_time)) {
      return(strings[[last_index - PREMATCH_LINKS_COUNT]])
    }

    last_string
  }


  get_match_datetime <- function(match_element) {
    rvest::html_text(match_element, ".game-time") %>%
      stringr::str_trim(.)  %>%
      stringr::str_split(., "\\n") %>%
      unlist(.) %>%
      purrr::map(., stringr::str_squish) %>%
      get_datetime_string(.)
  }


  parse_match_data <- function(index, match_element, roster_element) {
    match_datetime = get_match_datetime(match_element)
    team_elements = rvest::html_nodes(roster_element, "ul")

    # If the rosters for the given game haven't been announced yet, there will be no
    # <ul> element with roster info
    if (length(team_elements) == 0) {
      return(list())
    }

    team_roster_data <- team_elements %>%
      purrr::map(., parse_team_data) %>%
      purrr::map(., collect_players) %>%
      purrr::pmap(., assign_home_away_teams) %>%
      unlist(., recursive = FALSE) %>%
      purrr::map(., ~ c(., date = match_datetime, match_id = index))
  }


  collect_team_rosters <- function(html_page) {
    match_elements <- rvest::html_nodes(html_page, "#tteamlist .lineup-detail:not(.byes)")
    roster_elements <- rvest::html_nodes(html_page, "#tteamlist .list-inouts")
    match_indices <- 1:length(match_elements)

    list(match_indices, match_elements, roster_elements)
  }


  paste0(AFL_DOMAIN, TEAMS_PATH, "?round=", round_number) %>%
    xml2::read_html(.)  %>%
    collect_team_rosters %>%
    purrr::pmap(., parse_match_data) %>%
    convert_to_data_frame %>%
    clean_data_frame
}
