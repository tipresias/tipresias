FOOTY_WIRE_DOMAIN = "https://www.footywire.com"
BETTING_PATH = "/afl/footy/afl_betting"
BETTING_COL_NAMES = c(
  "Date",
  "Venue",
  "blank_one",
  "Team",
  "Score",
  "Margin",
  "Win Odds",
  "Win Paid",
  "Line Odds",
  "colon",
  "redundant_line_paid",
  "Line Paid",
  "blank_two",
  "blank_three",
  "Round",
  "Season"
)
COLS_TO_DROP = c(
  "blank_one", "colon", "redundant_line_paid", "blank_two", "blank_three"
)


#' Scrapes betting data from footywire, cleans it, and returns it
#' as a dataframe.
#' @param start_date Minimum match date for fetched data
#' @param end_date Maximum match date for fetched data
#' @export
fetch_betting_odds <- function(start_date, end_date) {
  slice_table_rows <- function(label_row_index_pair, table_rows) {
    slice_start <- label_row_index_pair[1]
    slice_end <- ifelse(
      is.na(label_row_index_pair[2]),
      length(table_rows),
      label_row_index_pair[2]
    )

    table_rows[slice_start:slice_end]
  }


  group_table_rows_by_round <- function(table_rows) {
    if (length(table_rows) == 0) {
      return(list(list()))
    }

    round_label_row_indices <- table_rows %>%
      purrr::map(~ rvest::html_node(., ".tbtitle")) %>%
      purrr::map(~ length(.) > 0) %>%
      unlist(.) %>%
      which(.)

    1:length(round_label_row_indices) %>%
      purrr::map(~ round_label_row_indices[.:(. + 1)]) %>%
      purrr::map(~ slice_table_rows(., table_rows))
  }


  contains_data_elements <- function(element) {
    element %>%
      rvest::html_nodes(., '.data') %>%
      length(.) > 0
  }


  parse_betting_data_rows <- function(round_rows) {
    if (length(round_rows) == 0) {
      return(list())
    }

    round_label <- round_rows[[1]] %>% rvest::html_text(.)

    round_rows %>%
      purrr::keep(., contains_data_elements) %>%
      purrr::map(rvest::html_text) %>%
      purrr::map(~ stringr::str_split(., "\\n")) %>%
      # str_split returns a list of length 1 that contains the split strings
      # for some reason. Unlisting the weirdly embedded list seems to be
      # the only thing that works
      purrr::map(unlist) %>%
      purrr::map(stringr::str_trim) %>%
      purrr::map(~ c(., round_label))
  }


  get_betting_table_rows <- function(page) {
    page %>%
      rvest::html_nodes(., "form table table table tr") %>%
      group_table_rows_by_round(.) %>%
      purrr::map(parse_betting_data_rows) %>%
      unlist(., recursive = FALSE)
  }


  fetch_betting_odds_page <- function(year) {
    year %>%
      paste0(FOOTY_WIRE_DOMAIN, BETTING_PATH, "?year=", .) %>%
      xml2::read_html(.) %>%
      get_betting_table_rows(.) %>%
      purrr::map(~ c(., year))
  }


  normalize_column_names <- function(data_frame) {
    dplyr::rename_all(
      data_frame,
      ~ stringr::str_to_lower(.) %>% stringr::str_replace_all(., "[.\\s]", "_")
    )
  }


  row_padding <- function(data_row, max_row_length) {
    pad_length = max_row_length - length(data_row)

    if (pad_length == 0) {
      return(list())
    }

    1:pad_length %>% purrr::map(~ NA)
  }


  normalize_row_length <- function(rows) {
    max_row_length <- rows %>%
      purrr::map(~ length(.)) %>%
      unlist(.) %>%
      max(.)

    rows %>% purrr::map(~ c(row_padding(., max_row_length), .))
  }


  drop_unwanted_columns <- function(betting_odds) {
    betting_odds[, !names(betting_odds) %in% COLS_TO_DROP]
  }


  get_year <- function(date) lubridate::ymd(date) %>% lubridate::year(.)


  return(
    get_year(start_date):get_year(end_date) %>%
      purrr::map(fetch_betting_odds_page) %>%
      unlist(., recursive = FALSE) %>%
      normalize_row_length %>%
      unlist(.) %>%
      matrix(
        .,
        ncol = length(BETTING_COL_NAMES),
        byrow = TRUE,
        dimnames = list(NULL, BETTING_COL_NAMES)
      ) %>%
      as.data.frame(.) %>%
      drop_unwanted_columns(.) %>%
      tidyr::fill(c(Date, Venue)) %>%
      dplyr::mutate(Date = lubridate::dmy(Date)) %>%
      dplyr::filter(., Date >= start_date & Date <= end_date) %>%
      normalize_column_names(.) %>%
      dplyr::mutate(
        venue = as.character(.$venue),
        team = as.character(.$team),
        score = as.character(.$score) %>% as.numeric(.),
        margin = stringr::str_replace_all(.$margin, '\\+', '') %>%
          as.character(.) %>%
          as.numeric(.),
        win_odds = as.character(.$win_odds) %>% as.numeric(.),
        win_paid = as.character(.$win_paid) %>% as.numeric(.),
        line_odds = stringr::str_replace_all(.$line_odds, '\\+', '') %>%
          as.character(.) %>%
          as.numeric(.),
        line_paid = as.character(.$line_paid) %>% as.numeric(.),
        round = as.character(.$round),
        season = as.character(.$season) %>% as.numeric(.)
      )
  )
}
