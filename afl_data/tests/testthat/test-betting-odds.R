EARLIEST_BETTING_DATA_SEASON <- 2010

describe("fetch_betting_odds()", {
  start_date <- "2008-01-01"
  end_date <- "2011-12-31"
  year_count <- 2

  # Fetching data takes awhile, so we do it once for all tests
  betting_odds_data <- fetch_betting_odds(
    start_date = start_date, end_date = end_date
  )

  it("returns a data.frame composed of match rows", {
    expect_true("data.frame" %in% class(betting_odds_data))
    # To make sure that data is organised by match, not by year
    expect_gt(length(betting_odds_data), year_count)
  })

  it("has the correct data type for each column", {
    expect_type(betting_odds_data$date, "double")
    expect_type(betting_odds_data$venue, "character")
    expect_type(betting_odds_data$home_team, "character")
    expect_type(betting_odds_data$away_team, "character")
    expect_type(betting_odds_data$home_score, "double")
    expect_type(betting_odds_data$away_score, "double")
    expect_type(betting_odds_data$home_margin, "double")
    expect_type(betting_odds_data$away_margin, "double")
    expect_type(betting_odds_data$home_win_odds, "double")
    expect_type(betting_odds_data$away_win_odds, "double")
    expect_type(betting_odds_data$home_win_paid, "double")
    expect_type(betting_odds_data$away_win_paid, "double")
    expect_type(betting_odds_data$home_line_odds, "double")
    expect_type(betting_odds_data$away_line_odds, "double")
    expect_type(betting_odds_data$home_line_paid, "double")
    expect_type(betting_odds_data$away_line_paid, "double")
    expect_type(betting_odds_data$round, "character")
    expect_type(betting_odds_data$round_number, "double")
    expect_type(betting_odds_data$season, "double")
  })

  it("returns a data.frame with rows from valid date range", {
    earliest_year <- betting_odds_data$date %>%
      purrr::map(lubridate::year) %>%
        unlist(.) %>%
        min(.)

    expect_true("data.frame" %in% class(betting_odds_data))
    expect_equal(earliest_year, EARLIEST_BETTING_DATA_SEASON)
  })
})
