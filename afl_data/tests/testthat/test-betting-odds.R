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
    expect_equal(class(betting_odds_data), "data.frame")
    # To make sure that data is organised by match, not by year
    expect_gt(length(betting_odds_data), year_count)
  })

  it("has the correct data type for each column", {
    expect_type(betting_odds_data$date, "double")
    expect_type(betting_odds_data$venue, "character")
    expect_type(betting_odds_data$team, "character")
    expect_type(betting_odds_data$score, "double")
    expect_type(betting_odds_data$margin, "double")
    expect_type(betting_odds_data$win_odds, "double")
    expect_type(betting_odds_data$win_paid, "double")
    expect_type(betting_odds_data$line_odds, "double")
    expect_type(betting_odds_data$line_paid, "double")
    expect_type(betting_odds_data$round, "character")
    expect_type(betting_odds_data$season, "double")
  })

  it("returns a data.frame with rows from valid date range", {
    earliest_year <- betting_odds_data$date %>%
      purrr::map(lubridate::year) %>%
        unlist(.) %>%
        min(.)

    expect_equal(class(betting_odds_data), "data.frame")
    expect_equal(earliest_year, EARLIEST_BETTING_DATA_SEASON)
  })
})
